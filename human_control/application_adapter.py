"""Synchronous, explicit connections to Phase 7; no State machine or resume engine.

Composition supplies the existing Use Cases and their repositories. Actual Outputs
are retained only in this process; SQLite contains references, never their contents.
The caller supplies formal inputs / Human decisions. Nothing derives them from UI
labels, an AI response, a State string, or a past Human Intent.
"""
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass, replace
from pathlib import Path
from uuid import UUID

from application.dto import (GenerateImplementationPlanInput, RequestPlanApprovalInput,
    ReviseImplementationPlanInput, GenerateCodexPromptInput)
from application.workflow_entry import WorkflowEntryInput, WorkflowEntryUseCase
from application.plan_workflow import PlanWorkflowUseCase, PlanWorkflowOutput
from application.implementation_workflow import ImplementationWorkflowUseCase, ImplementationWorkflowInput
from application.evidence_workflow import EvidenceWorkflowUseCase, EvidenceWorkflowInput
from application.implementation_evidence import EvidenceScope
from application.review_workflow import ReviewWorkflowUseCase, ReviewWorkflowInput, CorrectionStepInput
from application.final_approval_workflow import FinalApprovalWorkflowUseCase, HumanFinalDecisionInput
from application.workflow_trace import WorkflowTraceInput, WorkflowTraceUseCase
from human_control.projects import ProjectService
from human_control.workflows import WorkflowService, WorkflowBoundaryError, explicit_path


@dataclass(frozen=True)
class ApplicationPorts:
    entry: WorkflowEntryUseCase
    plans: PlanWorkflowUseCase
    implementation: ImplementationWorkflowUseCase
    evidence: EvidenceWorkflowUseCase
    review: ReviewWorkflowUseCase
    final: FinalApprovalWorkflowUseCase


@dataclass(frozen=True)
class DelegatedInputs:
    prompt: GenerateCodexPromptInput
    # Resolves explicit TDD facts against the actual generated Plan / Prompt.
    # Missing/non-unique facts must raise or return None, never guess a default.
    implementation: Callable[[PlanWorkflowOutput], ImplementationWorkflowInput]
    approved_scope: EvidenceScope
    source_paths: tuple[Path, ...]
    test_paths: tuple[Path, ...]
    review_mode: str


@dataclass(frozen=True)
class AdapterResult:
    workflow_id: UUID
    success: bool
    waiting_for_human: bool
    reason: str
    required_human_action: str
    outputs: tuple


class ApplicationAdapter:
    def __init__(self, workflows: WorkflowService, project_id: UUID,
                 workflow_id: UUID, ports: ApplicationPorts):
        self.workflows, self.project_id, self.workflow_id = workflows, project_id, workflow_id
        self.ports = ports
        self._outputs = []
        self._plan = self._review = self._final = None
        self._origin = None
        self._selected_paths = None

    def _result(self, success, waiting, reason='', action=''):
        return AdapterResult(self.workflow_id, success, waiting, reason, action,
                             deepcopy(tuple(self._outputs)))

    def _stop(self, error):
        return self._result(False, True, str(error),
            'Inspect the retained Phase 7 result and explicit artifact references; '
            'resolve the missing or mismatched input before choosing the next action.')

    def _binding(self):
        work, paths = self.workflows.binding(self.project_id, self.workflow_id)
        origin = (work.project_id, work.workflow_id, work.specification_path,
                  work.specification_hash, work.approval_id, work.state_path, work.history_path)
        if self._origin is not None and origin != self._origin:
            raise WorkflowBoundaryError('Workflow origin changed since this invocation began.')
        if self._selected_paths is not None and any(paths.get(role) != path
                for role, path in self._selected_paths.items()):
            raise WorkflowBoundaryError('Selected artifact references changed during this invocation.')
        return work, paths, origin

    @staticmethod
    def _match(value, paths, role, *, file=False, directory=False):
        if role not in paths or explicit_path(value) != paths[role]:
            raise WorkflowBoundaryError(f'Missing / mismatched explicit {role} reference.')
        if file and not paths[role].is_file():
            raise WorkflowBoundaryError(f'Required formal input is missing: {role}')
        if directory and not paths[role].is_dir():
            raise WorkflowBoundaryError(f'Required directory is missing: {role}')

    def _request_binding(self, request, paths):
        self._match(request.state_file, paths, 'state', file=True)
        self._match(request.state_history_dir, paths, 'history')

    def _keep(self, output):
        self._outputs.append(deepcopy(output))
        return output

    def _references(self, **paths):
        self.workflows.record_references(self.project_id, self.workflow_id,
                                        {k: v for k, v in paths.items() if v is not None})

    def start(self, request: GenerateImplementationPlanInput) -> AdapterResult:
        try:
            if self._outputs:
                raise WorkflowBoundaryError('Entry already attempted; this is not a Resume operation.')
            work, paths, origin = self._binding()
            gate = ProjectService(self.workflows.repository).workflow_start_gate(self.project_id)
            if not gate.allowed:
                raise WorkflowBoundaryError(f'Constitution confirmation required: {gate.unconfirmed}')
            self._request_binding(request, paths)
            for field, role in (('specification_path', 'specification'),
                ('constitution_path', 'constitution'), ('principles_path', 'principles'),
                ('decisions_path', 'decisions'), ('implementation_plan_template_path', 'plan_template'),
                ('template_path', 'plan_prompt_template')):
                self._match(getattr(request, field), paths, role, file=True)
            if (not isinstance(request.project_metadata, dict) or 'plan' not in paths
                    or any(not isinstance(request.project_metadata.get(key), str)
                           or not request.project_metadata[key].strip()
                           for key in ('project_name', 'target_path', 'project_description', 'project_version'))):
                raise WorkflowBoundaryError('Explicit Project metadata and Plan destination are required.')
            if paths['plan'].exists():
                raise WorkflowBoundaryError('New Plan destination already exists.')
            self._origin = origin
            self._selected_paths = dict(paths)
            entry = self._keep(self.ports.entry.execute(WorkflowEntryInput(
                paths['specification'], work.approval_id, paths['state'], paths['history'])))
            if not entry.can_generate_plan or entry.failures:
                return self._stop(entry.failures)
            # The actual saved record replaces caller-supplied approval claims.
            self._plan = self._keep(self.ports.plans.generate(entry,
                replace(request, specification_approval=entry.approval_record), paths['plan']))
            if not self._plan.success:
                return self._stop(self._plan.stop_reason)
            return self._result(True, True, 'Plan requires Human decision.',
                                'Review the saved Plan and explicitly approve, request revision, or cancel.')
        except Exception as exc:
            return self._stop(exc)

    def decide_plan(self, request: RequestPlanApprovalInput,
                    delegated: DelegatedInputs | None = None) -> AdapterResult:
        try:
            _, paths, _ = self._binding()
            if self._plan is None:
                raise WorkflowBoundaryError('No established Plan Output in this process.')
            self._request_binding(request, paths)
            self._match(request.implementation_plan_path, paths, 'plan', file=True)
            self._plan = self._keep(self.ports.plans.decide(self._plan, request))
            if not self._plan.success:
                return self._stop(self._plan.stop_reason)
            if self._plan.approval_result.decision == 'approved':
                if delegated is None:
                    return self._stop('Approved Plan retained; explicit delegated execution inputs are missing.')
                return self._delegated(delegated)
            return self._result(True, True, 'Human Plan decision returned by Phase 7.',
                                'Inspect the existing decision and supply revision inputs if requested.')
        except Exception as exc:
            return self._stop(exc)

    def revise_plan(self, request: ReviseImplementationPlanInput, revised_plan_path: Path) -> AdapterResult:
        try:
            _, paths, _ = self._binding()
            if self._plan is None:
                raise WorkflowBoundaryError('No established Human Revision Request.')
            self._request_binding(request, paths)
            self._match(request.specification_path, paths, 'specification', file=True)
            self._match(request.current_implementation_plan_path, paths, 'plan', file=True)
            self._match(request.revision_template_path, paths, 'revision_template', file=True)
            revised = explicit_path(revised_plan_path)
            # Reserve a Human-selected new destination before any Phase 7 writes.
            self._references(**{f'plan_revision_{len(self._outputs)}': revised})
            self._plan = self._keep(self.ports.plans.revise(self._plan, request, revised))
            if not self._plan.success:
                return self._stop(self._plan.stop_reason)
            self._references(plan=revised)
            self._selected_paths['plan'] = revised
            return self._result(True, True, 'Revised Plan requires new Human approval.',
                                'Review the new Plan artifact.')
        except Exception as exc:
            return self._stop(exc)

    def _delegated(self, inputs: DelegatedInputs):
        """Connect one explicitly delegated normal path; no inferred routing loop."""
        _, paths, _ = self._binding()
        self._request_binding(inputs.prompt, paths)
        for field, role in (('specification_path', 'specification'),
                            ('implementation_plan_path', 'plan'), ('template_path', 'prompt_template')):
            self._match(getattr(inputs.prompt, field), paths, role, file=True)
        self._match(inputs.prompt.implementation_target_path, paths, 'implementation_target')
        if (not callable(inputs.implementation) or not isinstance(inputs.approved_scope, EvidenceScope)
                or inputs.review_mode not in ('BATCH', 'STAGED')
                or not isinstance(inputs.source_paths, tuple) or not isinstance(inputs.test_paths, tuple)):
            raise WorkflowBoundaryError('Explicit execution, approved scope, source/test selections and Review mode required.')
        for role in ('repository', 'codex_prompt', 'review_dir', 'final_dir'):
            if role not in paths:
                raise WorkflowBoundaryError(f'Missing required formal reference: {role}')
        if not paths['repository'].is_dir():
            raise WorkflowBoundaryError('Target Repository is missing.')
        for value in (*inputs.source_paths, *inputs.test_paths):
            selected = explicit_path(value)
            if not selected.is_relative_to(paths['repository']):
                raise WorkflowBoundaryError('Source / test selection belongs to another Repository.')
        self._plan = self._keep(self.ports.plans.generate_prompt(self._plan, inputs.prompt))
        if not self._plan.success:
            return self._stop(self._plan.stop_reason)
        # Phase 7 generates the Prompt text; Evidence requires its actual file.
        # Create-only persistence preserves old artifacts and exposes write failure.
        with paths['codex_prompt'].open('xb') as stream:
            stream.write(self._plan.prompt_result.codex_prompt.encode('utf-8'))
        request = inputs.implementation(deepcopy(self._plan))
        if not isinstance(request, ImplementationWorkflowInput) or request.upstream != self._plan:
            raise WorkflowBoundaryError('Explicit Implementation inputs must bind to the current actual Plan Output.')
        self._match(request.repository, paths, 'repository', directory=True)
        # Recheck index identity after caller input acquisition, before execution.
        self._binding()
        implemented = self._keep(self.ports.implementation.execute(request))
        if not implemented.success:
            return self._stop(implemented.stop_reason)
        self._references(test_execution_record=implemented.execution.test_execution_record_path)
        evidence = self._keep(self.ports.evidence.execute(EvidenceWorkflowInput(implemented,
            paths['codex_prompt'], inputs.approved_scope, inputs.source_paths, inputs.test_paths)))
        if not evidence.success:
            return self._stop(evidence.stop_reason)
        self._references(evidence=evidence.collection.evidence_path, git_diff=evidence.collection.git_diff_path)
        self._review = self._keep(self.ports.review.start(ReviewWorkflowInput(
            evidence, inputs.review_mode, paths['review_dir'])))
        return self._after_review(paths)

    def _after_review(self, paths):
        if self._review.artifact_paths:
            self._references(review_snapshot=self._review.artifact_paths[-1])
        if not self._review.success:
            return self._stop(self._review.stop_reason)
        if not self._review.ready_for_final_approval:
            return self._result(True, True, 'Phase 7 Review / Correction Handoff retained.',
                'Inspect the existing Handoff and supply only explicitly established decisions or Correction inputs.')
        self._final = self._keep(self.ports.final.start(self._review, paths['final_dir']))
        if self._final.snapshot_path is not None:
            self._references(final_snapshot=self._final.snapshot_path)
        if not self._final.success:
            return self._stop(self._final.stop_reason)
        return self._result(True, True, 'Final Approval requires Human decision.',
                            'Inspect the existing Final Approval Target and its supported decisions.')

    def correct(self, request: CorrectionStepInput) -> AdapterResult:
        try:
            _, paths, _ = self._binding()
            if self._review is None:
                raise WorkflowBoundaryError('No established Review Output in this process.')
            self._review = self._keep(self.ports.review.correct(self._review, request))
            return self._after_review(paths)
        except Exception as exc:
            return self._stop(exc)

    def decide_final(self, human: HumanFinalDecisionInput) -> AdapterResult:
        try:
            _, paths, _ = self._binding()
            if self._final is None or not self._final.success or not self._final.waiting_for_human:
                raise WorkflowBoundaryError('No established waiting Final Approval Output in this process.')
            self._match(self._final.snapshot_path, paths, 'final_snapshot', file=True)
            # Phase 7 owns decision receipt, routing, Merge preconditions/retry and completion.
            # This call uses its existing waiting checkpoint, not a T5 Resume implementation.
            self._final = self._keep(self.ports.final.resume(self._final.snapshot_path, human))
            if not self._final.success:
                return self._stop(self._final.stop_reason)
            if self._final.completed:
                return self._result(True, False)
            return self._result(True, True, 'Existing Final Approval route retained; no inferred re-execution.',
                                'Inspect the existing routing destination and missing information.')
        except Exception as exc:
            return self._stop(exc)

    def trace(self):
        # Observation is not execution authorization. A changed Specification
        # must not hide the actual State / History and failed attempts.
        work = self.workflows.repository.get_workflow(self.workflow_id)
        if work.project_id != self.project_id:
            raise WorkflowBoundaryError('Project / Workflow ownership mismatch.')
        paths = self._selected_paths or dict(state=explicit_path(work.state_path),
                                            history=explicit_path(work.history_path))
        return WorkflowTraceUseCase().execute(WorkflowTraceInput(
            paths['state'], paths['history'], deepcopy(tuple(self._outputs))))
