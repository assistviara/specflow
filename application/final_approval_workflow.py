"""Phase 7 Target 6 integration; approval and Git rules belong to Phase 6."""
from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path
from uuid import uuid4
import os

from application.current_state_repository import load_current_state
from application.final_approval_entry import FinalApprovalEntryInput, FinalApprovalEntryUseCase
from application.final_approval_target import FinalApprovalTargetInput, FinalApprovalTargetOutput, FinalApprovalTargetUseCase
from application.review_handoff import HandoffType
from application.final_approval_target import artifact_hash, load_final_approval_target, _json_bytes
from application.final_approval_decision import FinalApprovalDecisionInput, FinalApprovalDecisionUseCase
from application.final_approval_record import FinalApprovalRecordInput, FinalApprovalRecordOutput, FinalApprovalRecordUseCase
from application.final_approval_routing import FinalApprovalRoutingInput, FinalApprovalRoutingOutput, FinalApprovalRoutingUseCase
from application.merge_preconditions import MergePreconditionsOutput, MergePreconditionsUseCase
from application.technical_merge_retry import TechnicalMergeRetryUseCase, MergeRetryOutput
from application.phase_six_completion import PhaseSixCompletionOutput, PhaseSixCompletionUseCase
from application.prepare_review_handoff import PrepareReviewHandoffUseCase
from application.implementation_evidence_serializer import implementation_evidence_from_dict
from application.final_approval_workflow_snapshot import save_checkpoint, load_checkpoint


@dataclass(frozen=True)
class HumanFinalDecisionInput:
    decision: str | None = None
    reason: str = ''
    approval_id: str = ''
    approved_at: str = ''
    comment: str = ''
    references: tuple[str, ...] = ()


@dataclass(frozen=True)
class FinalApprovalWorkflowOutput:
    success: bool = False
    waiting_for_human: bool = False
    target: FinalApprovalTargetOutput | None = None
    snapshot_path: Path | None = None
    current_state: dict | None = None
    stop_reason: str | None = None
    approval: FinalApprovalRecordOutput | None = None
    routing: FinalApprovalRoutingOutput | None = None
    ready: MergePreconditionsOutput | None = None
    merge: MergeRetryOutput | None = None
    completion: PhaseSixCompletionOutput | None = None
    completed: bool = False
    retry_snapshot_path: Path | None = None
    diagnostic_path: Path | None = None


class FinalApprovalWorkflowUseCase:
    def __init__(self, git, approvals, evidence, retry_repository_factory):
        self._git, self._approvals, self._evidence = git, approvals, evidence
        self._retry_repositories = retry_repository_factory

    def start(self, upstream, directory: Path) -> FinalApprovalWorkflowOutput:
        output = FinalApprovalWorkflowOutput()
        state_file = None
        try:
            if (not upstream.success or upstream.stop_reason or not upstream.ready_for_final_approval
                    or upstream.handoff.handoff_type != HandoffType.PHASE_6
                    or upstream.review is None or upstream.review.classification is None
                    or upstream.handoff.request.continuation.request.review != upstream.review.classification):
                raise ValueError('Successful current Target 5 PHASE_6 Handoff required')
            entry_request = upstream.request.upstream.request.upstream.request.upstream.entry.request
            state_file = entry_request.state_file
            state = load_current_state(state_file)
            output = replace(output, current_state=state)
            if state != upstream.current_state or state.get('status') != 'reviewing':
                raise ValueError('Current State must match Target 5 reviewing')
            inp = upstream.review.review.prepared.review_input
            collection = (upstream.cycles[-1].evidence if upstream.cycles
                          else upstream.request.upstream.collection)
            if (collection is None or not collection.success or collection.evidence_path is None
                    or collection.implementation_evidence != inp.evidence
                    or self._evidence.load(inp.evidence.identity.evidence_id) != inp.evidence
                    or (upstream.cycles and upstream.cycles[-1].re_review != upstream.review)):
                raise ValueError('Latest saved Evidence / Review mismatch')
            if not upstream.artifact_paths:
                raise ValueError('Saved Target 5 snapshot required')
            expected = asdict(upstream)
            expected['artifact_paths'] = upstream.artifact_paths[:-1]
            if json.loads(upstream.artifact_paths[-1].read_text(encoding='utf-8')) != json.loads(json.dumps(expected, default=str)):
                raise ValueError('Saved Target 5 snapshot mismatch')
            entry = FinalApprovalEntryUseCase(self._git).execute(FinalApprovalEntryInput(
                upstream.handoff, state_file, entry_request.history_dir))
            identity = str(uuid4())
            target = FinalApprovalTargetUseCase().execute(FinalApprovalTargetInput(entry,
                directory / f'target_{identity}.json', collection.evidence_path,
                inp.saved_diff.path, directory / f'report_{identity}.json'))
            output = replace(output, target=target, current_state=load_current_state(state_file))
            if not target.succeeded:
                raise ValueError(f'Entry / Target failed: {entry.failures}; {target.failures}')
            snapshot = directory / f'final_workflow_{identity}.json'
            output = replace(output, snapshot_path=snapshot)
            save_checkpoint(snapshot, target)
            if load_current_state(state_file) != output.current_state:
                raise ValueError('State changed while persisting Human waiting checkpoint')
            return replace(output, success=True, waiting_for_human=True)
        except Exception as exc:
            if state_file is not None:
                try:
                    output = replace(output, current_state=load_current_state(state_file))
                except Exception:
                    output = replace(output, current_state=None)
            return replace(output, stop_reason=f'{type(exc).__name__}: {exc}')

    def _validate_target(self, target):
        if not isinstance(target, FinalApprovalTargetOutput) or not target.succeeded:
            raise ValueError('Established saved Target required')
        entry = target.request.entry
        if not entry.entered or entry.failures:
            raise ValueError('Established saved Entry required')
        if load_current_state(entry.request.state_file).get('status') != 'final_approval_pending':
            raise ValueError('Current State must be final_approval_pending')
        checked = PrepareReviewHandoffUseCase().execute(entry.request.handoff.request)
        if checked.handoff_type != HandoffType.PHASE_6 or checked.failures:
            raise ValueError('Saved Handoff is not established')
        artifact = target.artifact
        if (load_final_approval_target(target.request.artifact_path) != artifact
                or artifact_hash(target.request.artifact_path) != target.artifact_hash):
            raise ValueError('Target / presented hash changed')
        review = entry.request.handoff.request.continuation.request.review
        inp = review.review.prepared.review_input
        identity = inp.evidence.identity
        if (artifact.head_commit != entry.head_commit or artifact.base_commit != identity.base_commit
                or artifact.implementation_branch != identity.implementation_branch
                or entry.request.handoff.request.implementation_id != identity.implementation_id):
            raise ValueError('Saved Target / Entry / Evidence identity mismatch')
        for name in ('implementation_evidence_reference', 'git_diff_reference', 'review_report_reference'):
            if getattr(artifact, name) != str(getattr(target.request, name)):
                raise ValueError('Saved Target reference mismatch')
        saved = implementation_evidence_from_dict(json.loads(Path(artifact.implementation_evidence_reference).read_text(encoding='utf-8')))
        if saved != inp.evidence or self._evidence.load(identity.evidence_id) != saved:
            raise ValueError('Saved Evidence mismatch')
        if Path(artifact.git_diff_reference).read_text(encoding='utf-8') != entry.repository_state.git_diff:
            raise ValueError('Saved Diff mismatch')
        if Path(artifact.review_report_reference).read_bytes() != _json_bytes(asdict(review.report)):
            raise ValueError('Saved Review Report mismatch')

    @staticmethod
    def _save_event(path, data):
        with path.open('x', encoding='utf-8') as stream:
            json.dump(data, stream, default=str, ensure_ascii=False, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())

    def _finish(self, output):
        if output.target is not None:
            try:
                state = load_current_state(output.target.request.entry.request.state_file)
                output = replace(output, current_state=state)
                expected = ('completed' if output.completed else
                    output.routing.transition['to_state'] if output.routing and output.routing.transition else
                    'final_approval_pending')
                if output.success and state.get('status') != expected:
                    output = replace(output, success=False, completed=False, waiting_for_human=False,
                        stop_reason='State changed during Target 6 processing')
            except Exception as exc:
                output = replace(output, success=False, completed=False, waiting_for_human=False, current_state=None,
                    stop_reason=f'{output.stop_reason or ""} State observation failed: {exc}')
        if output.snapshot_path is not None and output.snapshot_path.parent.is_dir():
            path = output.snapshot_path.parent / f'final_result_{uuid4()}.json'
            output = replace(output, diagnostic_path=path)
            try:
                self._save_event(path, asdict(output))
            except Exception as exc:
                output = replace(output, success=False, completed=False, waiting_for_human=False,
                    stop_reason=f'{output.stop_reason or ""} Result persistence failed: {exc}')
        return output

    def resume(self, snapshot_path: Path, human: HumanFinalDecisionInput | None = None):
        output = FinalApprovalWorkflowOutput(snapshot_path=snapshot_path)
        try:
            target = load_checkpoint(snapshot_path)
            if not isinstance(target, FinalApprovalTargetOutput):
                raise ValueError('Human waiting Target checkpoint required')
            output = replace(output, target=target)
            self._validate_target(target)
            receipt = snapshot_path.with_suffix('.decision.json')
            if receipt.exists():
                raise ValueError('Human decision already claimed; do not repeat Approval / Merge')
            human = human if human is not None else HumanFinalDecisionInput()
            decision = FinalApprovalDecisionUseCase().execute(FinalApprovalDecisionInput(target, human.decision))
            if decision.failures:
                raise ValueError(f'Explicit Human decision invalid: {decision.failures}')
            if decision.decision is None:
                return self._finish(replace(output, success=True, waiting_for_human=True))
            if not isinstance(human.reason, str) or not human.reason.strip():
                raise ValueError('Explicit Human routing reason required')
            if decision.is_final_approval:
                if (not isinstance(human.approval_id, str) or not human.approval_id.strip()
                        or any(c in human.approval_id for c in '/\\:')
                        or human.approval_id in ('.', '..')
                        or not isinstance(human.approved_at, str) or not human.approved_at.strip()):
                    raise ValueError('Explicit new Approval ID and approval time required')
                try:
                    existing = self._approvals.get(human.approval_id)
                except FileNotFoundError:
                    existing = None
                if existing is not None:
                    raise ValueError('Approval ID already exists; never overwrite an existing Approval')
            self._save_event(receipt, {'target_hash': target.artifact_hash, 'human': asdict(human)})
            if decision.is_final_approval:
                approval = FinalApprovalRecordUseCase(self._approvals).execute(FinalApprovalRecordInput(
                    decision, human.approval_id, human.approved_at, human.comment))
                output = replace(output, approval=approval)
                if not approval.approval_valid:
                    raise ValueError(f'Approval not valid: {approval.failures}')
            routing = FinalApprovalRoutingUseCase().execute(FinalApprovalRoutingInput(
                decision, human.reason, output.approval, human.references))
            output = replace(output, routing=routing)
            if not routing.routed:
                raise ValueError(f'Human routing failed: {routing.failures}')
            if not decision.is_final_approval:
                return self._finish(replace(output, success=True))
            ready = MergePreconditionsUseCase(self._git, self._approvals).execute(routing)
            output = replace(output, ready=ready)
            if not ready.merge_ready:
                raise ValueError(f'Merge not ready: {ready.failures}')
            ready_path = snapshot_path.with_suffix('.ready.json')
            output = replace(output, retry_snapshot_path=ready_path)
            save_checkpoint(ready_path, ready)
            service = TechnicalMergeRetryUseCase(self._git, self._approvals,
                self._retry_repositories(snapshot_path.parent / 'retry_history'))
            merged = service.start(ready)
            output = replace(output, merge=merged)
            self._save_event(ready_path.with_suffix('.operation.json'), {'operation_id': merged.operation_id})
            return self._complete(output)
        except Exception as exc:
            return self._finish(replace(output, success=False, stop_reason=f'{type(exc).__name__}: {exc}'))

    def _complete(self, output):
        if output.merge.failures or output.merge.result is None or not output.merge.result.succeeded:
            return self._finish(replace(output, success=False, stop_reason='Merge / verification stopped; inspect recorded operation before Human authorization'))
        completion = PhaseSixCompletionUseCase(self._approvals).execute(output.merge.result)
        return self._finish(replace(output, completion=completion, completed=completion.completed,
            success=completion.completed, stop_reason=None if completion.completed else f'Completion failed: {completion.failures}'))

    def retry(self, ready_path: Path, authorization=None):
        output = FinalApprovalWorkflowOutput(snapshot_path=ready_path, retry_snapshot_path=ready_path)
        try:
            ready = load_checkpoint(ready_path)
            if not isinstance(ready, MergePreconditionsOutput) or not ready.merge_ready or ready.failures:
                raise ValueError('Saved original pre-merge checkpoint required')
            target = ready.request.request.decision.request.target
            output = replace(output, target=target, ready=ready,
                routing=ready.request, approval=ready.request.request.approval)
            self._validate_target(target)
            pointer = json.loads(ready_path.with_suffix('.operation.json').read_text(encoding='utf-8'))
            if set(pointer) != {'operation_id'} or not isinstance(pointer['operation_id'], str):
                raise ValueError('Unique recorded operation required')
            service = TechnicalMergeRetryUseCase(self._git, self._approvals,
                self._retry_repositories(ready_path.parent / 'retry_history'))
            if authorization is not None:
                service.authorize(pointer['operation_id'], authorization)
            output = replace(output, merge=service.retry(pointer['operation_id'], ready))
            return self._complete(output)
        except Exception as exc:
            return self._finish(replace(output, success=False, stop_reason=f'{type(exc).__name__}: {exc}'))
