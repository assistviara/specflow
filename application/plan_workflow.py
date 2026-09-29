from dataclasses import dataclass, replace
from pathlib import Path

from application.current_state_repository import load_current_state
from application.dto import (
    GenerateImplementationPlanInput, GenerateImplementationPlanOutput,
    RequestPlanApprovalInput, RequestPlanApprovalOutput,
    ReviseImplementationPlanInput, ReviseImplementationPlanOutput,
    GenerateCodexPromptInput, GenerateCodexPromptOutput,
)
from application.workflow_entry import WorkflowEntryOutput
from core.approval_validation import validate_approval_result


@dataclass(frozen=True)
class PlanWorkflowOutput:
    entry: WorkflowEntryOutput
    plan_path: Path
    success: bool = False
    draft_result: GenerateImplementationPlanOutput | ReviseImplementationPlanOutput | None = None
    approval_result: RequestPlanApprovalOutput | None = None
    prompt_result: GenerateCodexPromptOutput | None = None
    state_before: dict | None = None
    current_state: dict | None = None
    stop_reason: str | None = None


class PlanWorkflowUseCase:
    """Connect Plan UseCases across explicit caller/Human interactions only."""

    def __init__(self, approvals, generation, approval, revision, prompt):
        self._approvals = approvals
        self._generation = generation
        self._approval = approval
        self._revision = revision
        self._prompt = prompt

    def _guard(self, output, request, expected_state):
        entry = output.entry
        if not entry.can_generate_plan or entry.failures:
            raise ValueError('Target 1 did not authorize Plan generation.')
        if (request.state_file != entry.request.state_file
                or request.state_history_dir != entry.request.history_dir):
            raise ValueError('Workflow State / History identity mismatch.')
        state = load_current_state(request.state_file)
        if not isinstance(state, dict) or state.get('status') != expected_state:
            raise ValueError(f'Current State must be {expected_state}.')
        return replace(output, state_before=state, current_state=state)

    def _validate(self, approval_id, path, kind):
        record = self._approvals.get(approval_id)
        if record is not None and record.get('approval_id') != approval_id:
            raise ValueError('Saved Approval ID mismatch.')
        result = validate_approval_result(record, str(path), kind)
        if not result.is_valid:
            raise ValueError('; '.join(result.validation_errors))
        return record

    def _specification(self, output, request):
        entry = output.entry
        if request.specification_path != entry.request.specification_path:
            raise ValueError('Specification path differs from Target 1.')
        return self._validate(entry.request.specification_approval_id,
                              request.specification_path, 'specification')

    def _finish(self, output, error=None):
        try:
            state = load_current_state(output.entry.request.state_file)
        except Exception as exc:
            state = None
            error = f'{error or ""} State observation failed: {type(exc).__name__}: {exc}'
        return replace(output, success=error is None, current_state=state, stop_reason=error)

    def _failed(self, output, stage, exc):
        # Existing UseCases may have saved State before History failed.
        # Re-observe it without claiming rollback or successful persistence.
        return self._finish(output, f'{stage}: {type(exc).__name__}: {exc}')

    @staticmethod
    def _save_draft(path, content):
        if not isinstance(content, str) or not content.strip():
            raise ValueError('Plan Draft is empty or unavailable.')
        # A revision uses a new artifact path, preserving the previous artifact.
        with path.open('xb') as stream:
            stream.write(content.encode('utf-8'))

    def generate(self, entry: WorkflowEntryOutput, request: GenerateImplementationPlanInput,
                 plan_path: Path) -> PlanWorkflowOutput:
        output = PlanWorkflowOutput(entry, plan_path)
        try:
            output = self._guard(output, request, 'plan_generating')
            record = self._specification(output, request)
            if plan_path.exists():
                raise ValueError('Plan artifact path already exists.')
            result = self._generation.execute(replace(request, specification_approval=record))
            output = replace(output, draft_result=result)
            if result is None or not result.success:
                raise ValueError(result.error_message if result else 'Specification approval invalid.')
            self._save_draft(plan_path, result.implementation_plan_draft)
            return self._finish(output)
        except Exception as exc:
            return self._failed(output, 'Plan generation / artifact persistence failed', exc)

    def decide(self, draft: PlanWorkflowOutput, request: RequestPlanApprovalInput) -> PlanWorkflowOutput:
        output = replace(draft, success=False, prompt_result=None, state_before=None)
        try:
            if not draft.success or draft.draft_result is None:
                raise ValueError('A successfully saved Plan Draft is required.')
            output = self._guard(output, request, 'plan_approval_pending')
            if request.implementation_plan_path != draft.plan_path:
                raise ValueError('Human Decision targets a different Plan artifact.')
            if request.human_decision not in ('approved', 'revision_requested', 'cancelled'):
                raise ValueError('An explicit supported Human Plan Decision is required.')
            result = self._approval.execute(request)
            output = replace(output, approval_result=result)
            if request.human_decision == 'approved':
                if not result.approval_valid:
                    raise ValueError('; '.join(result.approval_validation_result.validation_errors))
                saved = self._validate(request.approval_id, draft.plan_path, 'implementation_plan')
                if saved != result.approval_record:
                    raise ValueError('Saved Approval differs from the Human Decision record.')
            return self._finish(output)
        except Exception as exc:
            return self._failed(output, 'Human Plan Decision failed', exc)

    def revise(self, decision: PlanWorkflowOutput, request: ReviseImplementationPlanInput,
               revised_plan_path: Path) -> PlanWorkflowOutput:
        output = replace(decision, success=False, prompt_result=None, state_before=None)
        try:
            if (not decision.success or decision.approval_result is None
                    or decision.approval_result.decision != 'revision_requested'):
                raise ValueError('An explicit Human Revision Request is required.')
            output = self._guard(output, request, 'plan_revision_requested')
            self._specification(output, request)
            if (request.current_implementation_plan_path != decision.plan_path
                    or request.revision_request != decision.approval_result.revision_request):
                raise ValueError('Revision input differs from the Human Revision Request.')
            if revised_plan_path.exists():
                raise ValueError('Revised Plan requires a new artifact path.')
            result = self._revision.execute(request)
            output = replace(output, draft_result=result)
            if not result.success:
                raise ValueError(result.error_message)
            self._save_draft(revised_plan_path, result.revised_implementation_plan_draft)
            output = replace(output, plan_path=revised_plan_path, approval_result=None)
            return self._finish(output)
        except Exception as exc:
            return self._failed(output, 'Plan revision / artifact persistence failed', exc)

    def generate_prompt(self, approved: PlanWorkflowOutput,
                        request: GenerateCodexPromptInput) -> PlanWorkflowOutput:
        output = replace(approved, success=False, prompt_result=None, state_before=None)
        try:
            if (not approved.success or approved.approval_result is None
                    or approved.approval_result.decision != 'approved'
                    or not approved.approval_result.approval_valid):
                raise ValueError('An explicit valid Human Plan Approval is required.')
            output = self._guard(output, request, 'plan_approved')
            self._specification(output, request)
            if (request.implementation_plan_path != approved.plan_path
                    or request.specification_approval_id != approved.entry.request.specification_approval_id
                    or request.implementation_plan_approval_id != approved.approval_result.approval_record['approval_id']):
                raise ValueError('Prompt input artifact / approval identity mismatch.')
            saved = self._validate(request.implementation_plan_approval_id, approved.plan_path, 'implementation_plan')
            if saved != approved.approval_result.approval_record:
                raise ValueError('Saved Approval differs from the Human Decision record.')
            result = self._prompt.execute(request)
            output = replace(output, prompt_result=result)
            if not result.success or not result.prompt_usable:
                raise ValueError(result.stop_reason or result.error_message or 'Prompt is unusable.')
            return self._finish(output)
        except Exception as exc:
            return self._failed(output, 'Implementation Prompt generation failed', exc)
