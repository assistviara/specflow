"""Close Phase 6 only; no Git execution, retry or MVP completion judgment."""
from dataclasses import asdict, dataclass, replace
from datetime import datetime
import json
from pathlib import Path
from uuid import uuid4

from application.current_state_repository import load_current_state
from application.final_approval_decision import FinalApprovalDecisionUseCase
from application.final_approval_target import load_final_approval_target, _json_bytes
from application.implementation_evidence_serializer import implementation_evidence_from_dict
from application.merge_execution import MergeExecutionOutput
from application.prepare_review_handoff import PrepareReviewHandoffUseCase
from application.review_handoff import HandoffDiagnostic, HandoffType
from application.state_transition import transition_state
from core.approval_record_repository import ApprovalRecordRepository
from core.approval_validation import ApprovalValidationResult, validate_approval_result


@dataclass(frozen=True)
class PhaseSixCompletionOutput:
    # Retains Targets 1-7, references, Human Decision, Git facts and diagnostics.
    request: MergeExecutionOutput
    completed: bool = False
    final_state: str | None = None
    transition: dict | None = None
    approval_record: dict | None = None
    approval_validation: ApprovalValidationResult | None = None
    failures: tuple[HandoffDiagnostic, ...] = ()

    @property
    def required_human_action(self) -> tuple[str, ...]:
        return (('Inspect Phase 6 diagnostics and persisted State/History before deciding how to resume.',)
                if self.failures else ())


def _check_results(request: MergeExecutionOutput):
    if not isinstance(request, MergeExecutionOutput) or not request.succeeded:
        raise ValueError('Successful merge execution and post-merge verification are required')
    ready = request.request
    if (not ready.merge_ready or ready.failures or request.rechecked != ready
            or ready.approval_validation is None or not ready.approval_validation.is_valid
            or ready.pending_operations != () or ready.observed_repository is None
            or ready.observed_repository.git_status or ready.observed_repository.unavailable_evidence):
        raise ValueError('Successful Target 6 and immediate pre-merge recheck are required')
    route = ready.request
    received = route.request.decision
    if (not route.routed or route.destination != 'UC-12 Merge Approved Implementation'
            or route.transition is not None or not received.is_final_approval
            or FinalApprovalDecisionUseCase().execute(received.request) != received):
        raise ValueError('Explicit Human Final Approval route is required')
    approval = route.request.approval
    if (approval is None or not approval.approval_valid or approval.request.decision != received
            or approval.approval_record != ready.approval_record):
        raise ValueError('Matching saved Final Approval is required')
    target = received.request.target
    entry = target.request.entry
    if not target.succeeded or not entry.entered or entry.failures:
        raise ValueError('Established Final Approval Target and entry are required')
    handoff = entry.request.handoff
    checked = PrepareReviewHandoffUseCase().execute(handoff.request)
    if (handoff.handoff_type != HandoffType.PHASE_6 or handoff.failures
            or handoff.unresolved_issues or handoff.required_human_action
            or checked.handoff_type != HandoffType.PHASE_6 or checked.failures):
        raise ValueError('Phase 5 must be APPROVED without unresolved issues')
    artifact = target.artifact
    operation = request.operation
    verification = request.verification
    if (operation.operation != 'merge' or operation.target_branch != 'developer'
            or operation.source_branch != artifact.implementation_branch
            or operation.approved_commit != artifact.head_commit
            or not isinstance(operation.post_commit, str) or not operation.post_commit.strip()
            or operation.pre_commit != ready.observed_destination_head
            or not operation.pre_commit or ready.observed_head != artifact.head_commit
            or ready.observed_branch_head != artifact.head_commit
            or ready.observed_repository.branch != artifact.implementation_branch
            or ready.observed_repository.base_commit != artifact.base_commit):
        raise ValueError('Merge and preconditions must identify the approved implementation')
    if (verification.current_head != operation.post_commit
            or verification.target_head != operation.post_commit
            or verification.source_head != artifact.head_commit
            or verification.repository_state is None
            or verification.repository_state.branch != 'developer'
            or verification.repository_state.git_status
            or verification.repository_state.unavailable_evidence
            or verification.pending_operations != ()):
        raise ValueError('Complete post-merge identity and repository verification are required')
    return target, approval, received.review


class PhaseSixCompletionUseCase:
    def __init__(self, approvals: ApprovalRecordRepository) -> None:
        self._approvals = approvals

    def execute(self, request: MergeExecutionOutput) -> PhaseSixCompletionOutput:
        output = PhaseSixCompletionOutput(request)
        try:
            entry = request.request.request.request.decision.request.target.request.entry.request
            output = replace(output, final_state=load_current_state(entry.state_file).get('status'))
        except (OSError, ValueError, TypeError, AttributeError, KeyError) as exc:
            return replace(output, failures=(HandoffDiagnostic('STATE_READ_FAILED', str(exc)),))
        try:
            if output.final_state != 'final_approval_pending':
                raise ValueError('Current State must be final_approval_pending')
            target, approval, review = _check_results(request)
            artifact = target.artifact
            if load_final_approval_target(target.request.artifact_path) != artifact:
                raise ValueError('Current Target differs from the approved Artifact')
            inp = review.review.prepared.review_input
            for field in ('evidence', 'saved_diff', 'repository_state', 'specification',
                          'implementation_plan', 'codex_prompt', 'test_state'):
                if getattr(inp, field) is None:
                    raise ValueError(f'Required Review Input missing: {field}')
            identity = inp.evidence.identity
            if (identity.implementation_branch != artifact.implementation_branch
                    or identity.base_commit != artifact.base_commit
                    or target.request.entry.head_commit != artifact.head_commit):
                raise ValueError('Saved identity differs from the approved Target')
            for field in ('implementation_evidence_reference', 'git_diff_reference', 'review_report_reference'):
                if getattr(artifact, field) != str(getattr(target.request, field)):
                    raise ValueError(f'Target reference mismatch: {field}')
            evidence = implementation_evidence_from_dict(json.loads(
                Path(artifact.implementation_evidence_reference).read_text(encoding='utf-8')))
            if evidence != inp.evidence:
                raise ValueError('Evidence differs from the approved reference')
            if Path(artifact.git_diff_reference).read_text(encoding='utf-8') != target.request.entry.repository_state.git_diff:
                raise ValueError('Diff differs from the approved reference')
            if Path(artifact.review_report_reference).read_bytes() != _json_bytes(asdict(review.report)):
                raise ValueError('Review Report differs from the approved reference')
            record = self._approvals.get(approval.request.approval_id)
            output = replace(output, approval_record=record)
            validation = validate_approval_result(record, str(target.request.artifact_path), 'final_approval_target')
            output = replace(output, approval_validation=validation)
            if (not validation.is_valid or record != approval.approval_record
                    or record['artifact_hash'] != target.artifact_hash):
                raise ValueError('Saved Approval is not valid for the current approved Target')
        except Exception as exc:
            return replace(output, failures=(HandoffDiagnostic('COMPLETION_PRECONDITION_FAILED',
                f'{type(exc).__name__}: {exc}'),))

        transition = dict(transition_id=str(uuid4()), from_state='final_approval_pending', to_state='completed',
            occurred_at=datetime.now().astimezone().isoformat(),
            reason=(f'Phase 6 completed: approval {record["approval_id"]}; '
                    f'target {record["artifact_path"]}; hash {record["artifact_hash"]}; '
                    f'{artifact.implementation_branch}@{artifact.head_commit} -> '
                    f'developer@{request.operation.post_commit}'))
        output = replace(output, transition=transition)
        try:
            transition_state(entry.state_file, entry.history_dir, transition)
        except Exception as exc:
            output = replace(output, failures=(HandoffDiagnostic('STATE_HISTORY_PERSISTENCE_FAILED',
                f'{type(exc).__name__}: {exc}', (str(entry.state_file), str(entry.history_dir))),))
        # Observe partial persistence without undoing, repairing or retrying it.
        try:
            output = replace(output, final_state=load_current_state(entry.state_file).get('status'))
        except Exception as exc:
            output = replace(output, final_state=None, failures=(*output.failures,
                HandoffDiagnostic('FINAL_STATE_READ_FAILED', f'{type(exc).__name__}: {exc}')))
        if not output.failures and output.final_state != 'completed':
            output = replace(output, failures=(HandoffDiagnostic('FINAL_STATE_MISMATCH',
                'Persisted State does not confirm completed'),))
        return replace(output, completed=not output.failures and output.final_state == 'completed')
