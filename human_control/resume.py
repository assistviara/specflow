"""Read-only work continuity projection. No execution, repair, or Output synthesis.

The result describes established facts and a place to return Human attention.
It never authorizes execution: existing Use Cases must revalidate when invoked.
Only Phase 7's two fixed checkpoint types can be deserialized by its own loader.
Past Intent is display-only input from a future T6 reader; this module stores none.
"""
from copy import deepcopy
from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path
from uuid import UUID

from application.final_approval_decision import FinalApprovalDecisionInput, FinalApprovalDecisionUseCase
from application.final_approval_target import FinalApprovalTargetOutput
from application.final_approval_workflow import FinalApprovalWorkflowOutput
from application.final_approval_workflow_snapshot import load_checkpoint
from application.plan_workflow import PlanWorkflowOutput
from application.prepare_review_handoff import PrepareReviewHandoffUseCase
from application.prepare_review_input import PrepareReviewInputUseCase
from application.review_workflow import ReviewWorkflowOutput
from application.evidence_workflow import EvidenceWorkflowOutput
from application.workflow_trace import WorkflowTraceInput, WorkflowTraceUseCase
from core.approval_validation import validate_approval_result
from human_control.application_adapter import WorkflowObservation
from human_control.workflows import explicit_path
from infrastructure.git_repository_state_provider import GitRepositoryStateProvider
from infrastructure.json_test_state_provider import JsonTestStateProvider


@dataclass(frozen=True)
class PastHumanIntent:
    project_id: UUID
    workflow_id: UUID
    text: str


@dataclass(frozen=True)
class ResumeProjection:
    project_id: UUID
    workflow_id: UUID
    reconstructed: bool = False
    observed_state: dict | None = None
    history: tuple = ()
    resume_point: str | None = None
    facts: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = ()
    required_human_action: tuple[str, ...] = ()
    past_intent: PastHumanIntent | None = None
    checkpoint: Path | None = None
    recorded_return: dict | None = None
    completed: bool = False


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'Non-unique JSON field: {key}')
        result[key] = value
    return result


def _read(path):
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=_unique)


def _plain(value):
    return json.loads(json.dumps(asdict(value), default=str))


class ResumeService:
    def __init__(self, workflows, approvals, *, final_workflow=None, evidence_repository=None):
        self.workflows = workflows
        self.approvals = approvals
        self.final_workflow = final_workflow
        self.evidence_repository = evidence_repository

    @staticmethod
    def _same(value, expected, label):
        if explicit_path(value) != expected:
            raise ValueError(f'{label} reference mismatch')

    def _approval(self, identity, path, kind, expected=None):
        record = self.approvals.get(identity)
        if not isinstance(record, dict) or record.get('approval_id') != identity:
            raise ValueError(f'{kind}: saved Approval ID mismatch')
        validation = validate_approval_result(record, str(path), kind)
        if not validation.is_valid:
            raise ValueError(f'{kind}: {validation.validation_errors}')
        if expected is not None and record != expected:
            raise ValueError(f'{kind}: Approval Record changed since the actual Output')
        return record

    def _entry(self, entry, work, paths, approval):
        if not entry.can_generate_plan or entry.failures:
            raise ValueError('Existing Entry Output did not establish Plan generation')
        request = entry.request
        for value, role in ((request.state_file, 'state'), (request.history_dir, 'history'),
                            (request.specification_path, 'specification')):
            self._same(value, paths[role], role)
        if request.specification_approval_id != work.approval_id or entry.approval_record != approval:
            raise ValueError('Existing Entry Output belongs to a different Specification Approval')

    def _review_input(self, prepared, work, paths):
        if self.evidence_repository is None or prepared is None or prepared.review_input is None:
            raise ValueError('Existing Review input acquisition component / actual input is missing')
        request = prepared.acquired.request
        self._same(request.repository_path, paths['repository'], 'repository')
        inp = prepared.review_input
        basis = inp.evidence.basis
        self._same(basis.specification_path, paths['specification'], 'specification')
        self._same(basis.implementation_plan_path, paths['plan'], 'plan')
        self._same(basis.codex_prompt_path, paths['codex_prompt'], 'codex_prompt')
        self._same(inp.evidence.verification.test_execution_record_path,
                   paths['test_execution_record'], 'test_execution_record')
        if basis.specification_approval_id != work.approval_id:
            raise ValueError('Evidence belongs to a different Specification Approval')
        current = PrepareReviewInputUseCase(evidence_repository=self.evidence_repository,
            approval_repository=self.approvals,
            repository_state_provider=_ProjectionRepository(paths['repository']),
            test_state_provider_factory=lambda path, identity: JsonTestStateProvider(
                record_path=path, expected_implementation_id=identity)).execute(request)
        if (current.review_input is None or current.missing_information
                or current.acquisition_errors or current.mismatches):
            raise ValueError(f'Review input revalidation failed: {current.missing_information}; '
                             f'{current.acquisition_errors}; {current.mismatches}')
        if current.acquired != prepared.acquired or prepared.review_input != prepared.acquired:
            raise ValueError('Formal Review inputs changed since the actual Output')

    def _target_binding(self, target, paths):
        entry = target.request.entry.request
        self._same(entry.state_file, paths['state'], 'checkpoint State')
        self._same(entry.history_dir, paths['history'], 'checkpoint History')
        for value, role in ((target.request.implementation_evidence_reference, 'evidence'),
                            (target.request.git_diff_reference, 'git_diff')):
            self._same(value, paths[role], role)
        for path in (target.request.artifact_path, target.request.review_report_reference):
            if not explicit_path(path).is_relative_to(paths['final_dir']):
                raise ValueError('Final Approval artifact is outside its selected Workflow directory')

    def _return_record(self, checkpoint, target, paths, state):
        receipt_path = checkpoint.with_suffix('.decision.json')
        if not receipt_path.exists():
            if checkpoint.with_suffix('.ready.json').exists() or 'merge_checkpoint' in paths:
                raise ValueError('Pre-merge checkpoint exists without its Human decision receipt')
            if 'final_result' in paths:
                saved = _read(paths['final_result'])
                if (saved.get('success') is not True or saved.get('stop_reason')
                        or saved.get('target') != _plain(target) or saved.get('current_state') != state):
                    raise ValueError('Indexed Final result is failed, partial, or inconsistent')
                if saved.get('routing') is not None:
                    raise ValueError('Final result has a route but the Human decision receipt is missing')
            return None
        receipt = _read(receipt_path)
        if set(receipt) != {'target_hash', 'human'} or receipt['target_hash'] != target.artifact_hash:
            raise ValueError('Claimed Human decision receipt is incomplete or targets another Artifact')
        human = receipt['human']
        selection = FinalApprovalDecisionUseCase().execute(FinalApprovalDecisionInput(target, human.get('decision')))
        if selection.failures or selection.decision is None:
            raise ValueError('Saved Human decision is missing / ambiguous')
        if selection.is_final_approval:
            raise ValueError('Final decision already claimed; inspect actual Merge / Retry / Completion results. '
                             'Do not execute the checkpoint again.')
        if 'final_result' not in paths:
            raise ValueError('Human decision claimed but its indexed routing result is missing; no inferred return')
        saved = _read(paths['final_result'])
        self._same(saved['snapshot_path'], checkpoint, 'Final result checkpoint')
        self._same(saved['diagnostic_path'], paths['final_result'], 'Final result diagnostic')
        if saved['target'] != _plain(target) or saved['current_state'] != state:
            raise ValueError('Saved Final result target / State mismatch')
        route = saved.get('routing')
        if (not route or route['request']['decision'] != _plain(selection)
                or route['request']['reason'] != human['reason']
                or route['request']['references'] != human['references']):
            raise ValueError('Saved return does not correspond to the recorded Human decision')
        # Display the existing result verbatim. Never invoke routing to reproduce it.
        return dict(decision=selection.decision.value, destination=route.get('destination'),
                    reason=route['request']['reason'], failures=route.get('failures'),
                    stop_reason=saved.get('stop_reason'), references=route['request']['references'],
                    result_success=saved.get('success'))

    def project(self, project_id: UUID, workflow_id: UUID, *,
                observation: WorkflowObservation | None = None,
                past_intent: PastHumanIntent | None = None) -> ResumeProjection:
        output = ResumeProjection(project_id, workflow_id)
        try:
            work = self.workflows.repository.get_workflow(workflow_id)
            if work.project_id != project_id:
                raise ValueError('Project / Workflow ownership mismatch')
            self.workflows.repository.get_project(project_id)
            if past_intent is not None:
                if (not isinstance(past_intent, PastHumanIntent)
                        or (past_intent.project_id, past_intent.workflow_id) != (project_id, workflow_id)
                        or not isinstance(past_intent.text, str)):
                    raise ValueError('Past Human Intent ownership / representation mismatch')
                output = replace(output, past_intent=deepcopy(past_intent))
            if observation is not None and (not isinstance(observation, WorkflowObservation)
                    or (observation.project_id, observation.workflow_id) != (project_id, workflow_id)):
                raise ValueError('In-process observation ownership mismatch')
            actual = deepcopy(observation.outputs) if observation is not None else ()
            trace = WorkflowTraceUseCase().execute(WorkflowTraceInput(
                explicit_path(work.state_path), explicit_path(work.history_path), actual))
            output = replace(output, observed_state=deepcopy(trace.current_state), history=trace.history,
                facts=tuple(f"History: {item.record['from_state']} -> {item.record['to_state']}"
                            for item in trace.history if item.error is None))
            # Retain observed facts even when origin validation subsequently fails.
            work, paths = self.workflows.binding(project_id, workflow_id)
            approval = self._approval(work.approval_id, paths['specification'], 'specification')
            diagnostics = tuple(d for d in trace.diagnostics
                                if not (not actual and d == 'WORKFLOW_OUTPUT_MISSING'))
            if diagnostics:
                return replace(output, diagnostics=diagnostics,
                    required_human_action=('Inspect State, History and actual Output inconsistencies; no repair or execution was performed.',))
            if actual:
                latest = actual[-1]
                if isinstance(latest, PlanWorkflowOutput):
                    self._entry(latest.entry, work, paths, approval)
                    self._same(latest.plan_path, paths['plan'], 'Plan')
                    if not latest.success or latest.stop_reason or latest.draft_result is None:
                        raise ValueError('Successful actual Plan Draft Output is required')
                    draft = latest.draft_result
                    content = (draft.implementation_plan_draft if hasattr(draft, 'implementation_plan_draft')
                               else draft.revised_implementation_plan_draft)
                    if not isinstance(content, str) or paths['plan'].read_bytes() != content.encode('utf-8'):
                        raise ValueError('Saved Plan differs from its actual Draft Output')
                    if latest.approval_result is None and latest.prompt_result is None:
                        if trace.current_state['status'] != 'plan_approval_pending':
                            raise ValueError('Actual Plan Output is not at its existing Human waiting point')
                        return replace(output, reconstructed=True, resume_point='PLAN_APPROVAL',
                            required_human_action=('Review the actual Plan; explicitly approve, request revision, or cancel through the existing Use Case.',))
                    raise ValueError('Plan continuation requires its explicit next inputs; do not replay the previous Human decision')
                if isinstance(latest, (ReviewWorkflowOutput, EvidenceWorkflowOutput)):
                    if not latest.success or latest.stop_reason:
                        raise ValueError(latest.stop_reason or 'Latest Application Output is not successful')
                    prepared = (latest.review.review.prepared if isinstance(latest, ReviewWorkflowOutput)
                                else latest.handoff)
                    self._review_input(prepared, work, paths)
                    if isinstance(latest, ReviewWorkflowOutput):
                        checked = PrepareReviewHandoffUseCase().execute(latest.handoff.request)
                        if checked != latest.handoff or checked.failures:
                            raise ValueError('Existing Review Handoff revalidation failed')
                        return replace(output, reconstructed=True, resume_point='REVIEW_HANDOFF',
                            required_human_action=checked.required_human_action or
                                ('Inspect the existing Handoff; downstream execution still requires its existing entry validation.',))
                    return replace(output, reconstructed=True, resume_point='REVIEW_INPUT',
                        required_human_action=('Continue only through the existing Review entry with explicit delegated inputs.',))
                if not isinstance(latest, FinalApprovalWorkflowOutput):
                    raise ValueError('No supported safe continuation with the retained upstream Output and inputs')
                if not latest.success or latest.stop_reason:
                    raise ValueError(latest.stop_reason or 'Latest Final Approval Output failed')
                if latest.completed:
                    # Completion observation requires more than a State or checkpoint.
                    # Its existing workflow result is retained; do not run completion again.
                    raise ValueError('Completed result retained in Trace; no automatic execution or checkpoint replay is available')
            if 'final_snapshot' not in paths:
                raise ValueError('UPSTREAM_OUTPUT_MISSING: no actual Output or supported indexed checkpoint')
            checkpoint = paths['final_snapshot']
            output = replace(output, checkpoint=checkpoint)
            if not checkpoint.is_relative_to(paths['final_dir']):
                raise ValueError('Checkpoint does not belong to the selected Final Approval directory')
            target = load_checkpoint(checkpoint)
            if type(target) is not FinalApprovalTargetOutput:
                raise ValueError('This is not a Human waiting Target checkpoint; operation-specific review is required')
            self._target_binding(target, paths)
            if actual and (actual[-1].snapshot_path != checkpoint or actual[-1].target != target):
                raise ValueError('Actual Final Output differs from its indexed checkpoint')
            recorded = self._return_record(checkpoint, target, paths, trace.current_state)
            output = replace(output, recorded_return=recorded)
            if recorded and (recorded['result_success'] is not True or recorded['failures']
                             or recorded['stop_reason'] or not recorded['destination']):
                raise ValueError('Recorded Human return is failed / partial; inspect the retained result')
            if self.final_workflow is None:
                raise ValueError('Existing Final Approval validation component is required')
            # Deliberate reuse of Phase 7's read-only helper. Do not copy its logic
            # or call resume(), whose _finish() persists diagnostic artifacts.
            self.final_workflow._validate_target(target)
            prepared = target.request.entry.request.handoff.request.continuation.request.review.review.prepared
            self._review_input(prepared, work, paths)
            return replace(output, reconstructed=True,
                resume_point='HUMAN_HANDOFF' if recorded else 'FINAL_APPROVAL',
                required_human_action=(('Inspect the recorded return destination and unresolved information; no destination process was started.',)
                    if recorded else ('Inspect the restored Final Approval Target; supply an explicit Human decision to the existing Use Case.',)))
        except Exception as exc:
            return replace(output, reconstructed=False, resume_point=None, completed=False,
                diagnostics=(*output.diagnostics, f'{type(exc).__name__}: {exc}'),
                required_human_action=('Resolve the reported missing or inconsistent formal inputs with Human judgment; no execution or repair was performed.',))


class _ProjectionRepository(GitRepositoryStateProvider):
    """Keep Phase 7's observation logic, suppress optional Git index writes."""
    def _run_git(self, *arguments):
        return super()._run_git('--no-optional-locks', *arguments)
