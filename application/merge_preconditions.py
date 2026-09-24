"""Read-only checks immediately before merge; never merge or change State."""
from dataclasses import asdict, dataclass
import json
from pathlib import Path

from application.current_state_repository import load_current_state
from application.final_approval_decision import FinalApprovalDecisionUseCase
from application.final_approval_routing import FinalApprovalRoutingOutput
from application.final_approval_target import load_final_approval_target, _json_bytes
from application.git_merge_service import GitMergeService
from application.implementation_evidence_serializer import implementation_evidence_from_dict
from application.prepare_review_handoff import PrepareReviewHandoffUseCase
from application.repository_state_provider import RepositoryState
from application.review_handoff import HandoffType
from core.approval_record_repository import ApprovalRecordRepository
from core.approval_validation import ApprovalValidationResult, validate_approval_result


@dataclass(frozen=True)
class PreconditionFailure:
    code: str
    detail: str


@dataclass(frozen=True)
class MergePreconditionsOutput:
    request: FinalApprovalRoutingOutput
    merge_ready: bool = False
    approval_record: dict | None = None
    approval_validation: ApprovalValidationResult | None = None
    observed_repository: RepositoryState | None = None
    observed_head: str | None = None
    observed_branch_head: str | None = None
    observed_destination_head: str | None = None
    pending_operations: tuple[str, ...] | None = None
    failures: tuple[PreconditionFailure, ...] = ()


class MergePreconditionsUseCase:
    def __init__(self, git: GitMergeService, approvals: ApprovalRecordRepository) -> None:
        self._git = git
        self._approvals = approvals

    def execute(self, request: FinalApprovalRoutingOutput) -> MergePreconditionsOutput:
        failures = []
        def fail(code, detail):
            failures.append(PreconditionFailure(code, detail))

        record = validation = None
        try:
            if (not isinstance(request, FinalApprovalRoutingOutput) or not request.routed
                    or request.destination != 'UC-12 Merge Approved Implementation'
                    or request.transition is not None):
                raise ValueError('A successful Final Approval route is required')
            received = request.request.decision
            if (not received.is_final_approval
                    or FinalApprovalDecisionUseCase().execute(received.request) != received):
                raise ValueError('Explicit Human Final Approval is required')
            approval = request.approval_for_next_stage
            if approval is None or not approval.approval_valid or approval.request.decision != received:
                raise ValueError('Matching saved and validated Target 4 Approval is required')
            target = received.request.target
            artifact = target.artifact
            entry = target.request.entry
            if not entry.entered or entry.failures:
                raise ValueError('Successful Final Approval entry is required')
            if load_current_state(entry.request.state_file).get('status') != 'final_approval_pending':
                raise ValueError('Current State must be final_approval_pending')
            handoff = entry.request.handoff
            checked = PrepareReviewHandoffUseCase().execute(handoff.request)
            if (handoff.handoff_type != HandoffType.PHASE_6 or handoff.failures
                    or handoff.unresolved_issues or handoff.required_human_action
                    or checked.handoff_type != HandoffType.PHASE_6 or checked.failures):
                raise ValueError('Phase 5 Review has missing information or unresolved issues')
            review = received.review
            inp = review.review.prepared.review_input
            for name in ('evidence', 'saved_diff', 'repository_state', 'specification',
                         'implementation_plan', 'codex_prompt', 'test_state'):
                if getattr(inp, name) is None:
                    raise ValueError(f'Review Input missing: {name}')
            identity = inp.evidence.identity
            if (identity.implementation_branch != artifact.implementation_branch
                    or identity.base_commit != artifact.base_commit
                    or entry.head_commit != artifact.head_commit):
                raise ValueError('Saved Implementation identity differs from approved Target')
            if load_final_approval_target(target.request.artifact_path) != artifact:
                raise ValueError('Saved Target Artifact differs from approved Target')
            for field in ('implementation_evidence_reference', 'git_diff_reference', 'review_report_reference'):
                if getattr(artifact, field) != str(getattr(target.request, field)):
                    raise ValueError(f'Target reference mismatch: {field}')
            evidence = implementation_evidence_from_dict(json.loads(
                Path(artifact.implementation_evidence_reference).read_text(encoding='utf-8')))
            if evidence != inp.evidence:
                raise ValueError('Saved Evidence differs from approved Evidence')
            approved_diff = Path(artifact.git_diff_reference).read_text(encoding='utf-8')
            if approved_diff != entry.repository_state.git_diff:
                raise ValueError('Saved Diff differs from approved Diff')
            if Path(artifact.review_report_reference).read_bytes() != _json_bytes(asdict(review.report)):
                raise ValueError('Saved Review Report differs from approved Review Report')
        except (OSError, ValueError, TypeError, AttributeError, KeyError, IndexError) as exc:
            return MergePreconditionsOutput(request, failures=(PreconditionFailure(
                'INPUT_PRECONDITION_FAILED', f'{type(exc).__name__}: {exc}'),))

        try:
            record = self._approvals.get(approval.request.approval_id)
            validation = validate_approval_result(record, str(target.request.artifact_path), 'final_approval_target')
            if not validation.is_valid:
                fail('APPROVAL_INVALID', '; '.join(validation.validation_errors))
            if record != approval.approval_record or record is None or record.get('artifact_hash') != target.artifact_hash:
                fail('APPROVAL_MISMATCH', 'Saved Approval differs from the Human-approved Target 4 record')
        except Exception as exc:
            fail('APPROVAL_UNAVAILABLE', f'{type(exc).__name__}: {exc}')
        if failures:
            return MergePreconditionsOutput(request, approval_record=record,
                approval_validation=validation, failures=tuple(failures))

        # Retain independent observations, including those acquired when another
        # operation fails. Never replace saved identity with these current facts.
        observed = head = branch_head = destination_head = pending = None
        try:
            observed = self._git.get_state(artifact.base_commit)
            if not isinstance(observed, RepositoryState):
                raise ValueError('RepositoryState unavailable')
            if observed.unavailable_evidence:
                fail('REPOSITORY_INFORMATION_MISSING', repr(observed.unavailable_evidence))
            if not observed.branch or observed.branch != artifact.implementation_branch:
                fail('BRANCH_MISMATCH', repr(observed.branch))
            if not observed.base_commit or observed.base_commit != artifact.base_commit:
                fail('BASE_COMMIT_MISMATCH', repr(observed.base_commit))
            if observed.git_diff != approved_diff:
                fail('DIFF_MISMATCH', 'Observed Diff differs from approved Diff')
            if observed.git_status:
                fail('WORKING_TREE_NOT_READY', observed.git_status)
        except Exception as exc:
            fail('REPOSITORY_ACCESS_FAILED', f'{type(exc).__name__}: {exc}')
        try:
            head = self._git.get_current_head()
            if not isinstance(head, str) or not head.strip() or head != artifact.head_commit:
                fail('HEAD_MISMATCH', repr(head))
        except Exception as exc:
            fail('HEAD_UNAVAILABLE', f'{type(exc).__name__}: {exc}')
        for branch, is_source in ((artifact.implementation_branch, True), ('developer', False)):
            try:
                value = self._git.get_branch_head(branch)
                if is_source:
                    branch_head = value
                else:
                    destination_head = value
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(f'Branch unavailable: {branch}')
                if is_source and value != artifact.head_commit:
                    fail('BRANCH_HEAD_MISMATCH', value)
            except Exception as exc:
                fail('SOURCE_BRANCH_UNAVAILABLE' if is_source else 'DESTINATION_BRANCH_UNAVAILABLE',
                    f'{type(exc).__name__}: {exc}')
        try:
            pending = self._git.get_pending_operations()
            if not isinstance(pending, tuple):
                raise ValueError('Pending operation information unavailable')
            if pending:
                fail('REPOSITORY_OPERATION_PENDING', repr(pending))
        except Exception as exc:
            fail('REPOSITORY_SAFETY_UNAVAILABLE', f'{type(exc).__name__}: {exc}')
        return MergePreconditionsOutput(request, not failures, record, validation,
            observed, head, branch_head, destination_head, pending, tuple(failures))
