"""Route explicit Human decisions without executing the destination process."""
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from application.correction_routing import ReturnDestination
from application.current_state_repository import load_current_state
from application.final_approval_decision import (
    FinalApprovalDecision, FinalApprovalDecisionOutput, FinalApprovalDecisionUseCase,
)
from application.final_approval_record import FinalApprovalRecordOutput
from application.state_transition import transition_state
from core.approval_validation import validate_approval_result


@dataclass(frozen=True)
class FinalApprovalRoutingInput:
    decision: FinalApprovalDecisionOutput
    reason: str
    # Retained as context on return routes, never approval for a changed Artifact.
    approval: FinalApprovalRecordOutput | None = None
    references: tuple[str, ...] = ()


@dataclass(frozen=True)
class RoutingFailure:
    code: str
    detail: str


@dataclass(frozen=True)
class FinalApprovalRoutingOutput:
    # Preserves the Human decision, reason, Target, Approval and all references.
    request: FinalApprovalRoutingInput
    destination: str | None = None
    transition: dict | None = None
    failures: tuple[RoutingFailure, ...] = ()

    @property
    def routed(self) -> bool:
        return self.destination is not None and not self.failures

    @property
    def approval_for_next_stage(self) -> FinalApprovalRecordOutput | None:
        if self.routed and self.request.decision.is_final_approval:
            return self.request.approval
        return None


class FinalApprovalRoutingUseCase:
    def execute(self, request: FinalApprovalRoutingInput) -> FinalApprovalRoutingOutput:
        try:
            received = request.decision
            if (not isinstance(received, FinalApprovalDecisionOutput)
                    or not isinstance(received.decision, FinalApprovalDecision)
                    or received.failures
                    or FinalApprovalDecisionUseCase().execute(received.request) != received):
                raise ValueError('An explicit decision received by Target 3 is required')
            if not isinstance(request.reason, str) or not request.reason.strip():
                raise ValueError('An explicit routing reason is required')
            entry = received.request.target.request.entry.request
            if load_current_state(entry.state_file).get('status') != 'final_approval_pending':
                raise ValueError('Current State must be final_approval_pending')
        except (OSError, ValueError, TypeError, AttributeError, KeyError) as exc:
            return FinalApprovalRoutingOutput(request, failures=(RoutingFailure(
                'ROUTING_INPUT_INVALID', f'{type(exc).__name__}: {exc}'),))

        decision = received.decision
        if decision is FinalApprovalDecision.FINAL_APPROVAL:
            try:
                approval = request.approval
                if (not isinstance(approval, FinalApprovalRecordOutput)
                        or not approval.approval_valid or approval.request.decision != received):
                    raise ValueError('A valid Target 4 result for this Human decision is required')
                target = received.request.target
                record = approval.approval_record
                if record is None or record['artifact_hash'] != target.artifact_hash:
                    raise ValueError('Approval must identify the Target presented to Human')
                # Recheck Artifact bytes to avoid forwarding a stale validation
                # result. This performs no Git observation or merge readiness.
                validation = validate_approval_result(record, str(target.request.artifact_path), 'final_approval_target')
                if not validation.is_valid:
                    raise ValueError('; '.join(validation.validation_errors))
            except (OSError, ValueError, TypeError, AttributeError, KeyError) as exc:
                return FinalApprovalRoutingOutput(request, failures=(RoutingFailure(
                    'FINAL_APPROVAL_NOT_VALID', f'{type(exc).__name__}: {exc}'),))
            return FinalApprovalRoutingOutput(request, 'UC-12 Merge Approved Implementation')

        if decision is FinalApprovalDecision.PLAN_REVISION:
            return FinalApprovalRoutingOutput(request, ReturnDestination.PLAN)
        if decision is FinalApprovalDecision.SPECIFICATION_RECONSIDERATION:
            return FinalApprovalRoutingOutput(request, ReturnDestination.SPECIFICATION)

        # These are the only two Target 5 decisions that own state transitions.
        correction = decision is FinalApprovalDecision.IMPLEMENTATION_CORRECTION
        destination = ReturnDestination.IMPLEMENTATION if correction else 'cancelled'
        transition = dict(transition_id=str(uuid4()), from_state='final_approval_pending',
            to_state='correction_requested' if correction else 'cancelled',
            occurred_at=datetime.now().astimezone().isoformat(), reason=request.reason)
        try:
            transition_state(entry.state_file, entry.history_dir, transition)
        except Exception as exc:
            # State may already be saved when history fails. Preserve the
            # attempted transition without rollback, retry or a successful route.
            return FinalApprovalRoutingOutput(request, transition=transition, failures=(RoutingFailure(
                'STATE_HISTORY_PERSISTENCE_FAILED', f'{type(exc).__name__}: {exc}'),))
        return FinalApprovalRoutingOutput(request, destination, transition)
