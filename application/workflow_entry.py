from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from application.current_state_repository import load_current_state
from application.state_transition import transition_state
from core.approval_record_repository import ApprovalRecordRepository
from core.approval_validation import ApprovalValidationResult, validate_approval_result


@dataclass(frozen=True)
class WorkflowEntryInput:
    specification_path: Path | None
    specification_approval_id: str
    state_file: Path
    history_dir: Path


@dataclass(frozen=True)
class WorkflowEntryFailure:
    code: str
    detail: str


@dataclass(frozen=True)
class WorkflowEntryOutput:
    request: WorkflowEntryInput
    can_generate_plan: bool = False
    approval_record: dict | None = None
    approval_validation: ApprovalValidationResult | None = None
    current_state: dict | None = None
    transition: dict | None = None
    failures: tuple[WorkflowEntryFailure, ...] = ()


class WorkflowEntryUseCase:
    """Validate entry and persist readiness; never generate a Plan or approval."""

    def __init__(self, approvals: ApprovalRecordRepository) -> None:
        self._approvals = approvals

    def execute(self, request: WorkflowEntryInput) -> WorkflowEntryOutput:
        record = None
        validation = None
        state = None
        transition = None

        def stop(code, detail):
            return WorkflowEntryOutput(
                request, approval_record=record, approval_validation=validation,
                current_state=state, transition=transition,
                failures=(WorkflowEntryFailure(code, detail),),
            )

        if request.specification_path is None or not str(request.specification_path).strip():
            return stop('SPECIFICATION_NOT_SPECIFIED', 'An explicit Specification path is required.')
        try:
            artifact = Path(request.specification_path)
            if not artifact.exists():
                return stop('SPECIFICATION_NOT_FOUND', str(artifact))
            if not artifact.is_file():
                return stop('SPECIFICATION_IDENTITY_UNAVAILABLE', 'Specification must be a file.')
        except (OSError, TypeError, ValueError) as exc:
            return stop('SPECIFICATION_IDENTITY_UNAVAILABLE', str(exc))

        if not request.specification_approval_id:
            return stop('APPROVAL_NOT_FOUND', 'A saved Specification Approval ID is required.')
        try:
            record = self._approvals.get(request.specification_approval_id)
        except FileNotFoundError:
            return stop('APPROVAL_NOT_FOUND', request.specification_approval_id)
        except Exception as exc:
            return stop('APPROVAL_LOAD_FAILED', f'{type(exc).__name__}: {exc}')
        if record is not None:
            if not isinstance(record, dict):
                return stop('APPROVAL_VALIDATION_FAILED', 'Approval Record must be a mapping.')
            if record.get('approval_id') != request.specification_approval_id:
                return stop('APPROVAL_ID_MISMATCH', 'Loaded Approval ID differs from the requested ID.')
        try:
            # Validate saved identity against current bytes without rewriting it.
            validation = validate_approval_result(record, str(artifact), 'specification')
        except Exception as exc:
            return stop('APPROVAL_VALIDATION_FAILED', f'{type(exc).__name__}: {exc}')
        if not validation.is_valid:
            return stop('APPROVAL_INVALID', '; '.join(validation.validation_errors))

        try:
            state = load_current_state(request.state_file)
        except Exception as exc:
            return stop('STATE_LOAD_FAILED', f'{type(exc).__name__}: {exc}')
        if not isinstance(state, dict) or state.get('status') != 'specification_ready':
            return stop('STATE_MISMATCH', 'Current State must be specification_ready.')

        transition = dict(
            transition_id=str(uuid4()), from_state='specification_ready',
            to_state='plan_generating', occurred_at=datetime.now().astimezone().isoformat(),
            reason=f'Workflow entry validated Specification {artifact}; approval {request.specification_approval_id}',
        )
        try:
            transition_state(request.state_file, request.history_dir, transition)
        except Exception as exc:
            # The helper saves State before History. Preserve the attempted
            # transition and re-observe State; never infer success or roll back.
            try:
                state = load_current_state(request.state_file)
            except Exception:
                state = None
            return stop('STATE_HISTORY_PERSISTENCE_FAILED', f'{type(exc).__name__}: {exc}')
        return WorkflowEntryOutput(
            request, can_generate_plan=True, approval_record=record,
            approval_validation=validation, current_state={**state, 'status': 'plan_generating'},
            transition=transition,
        )
