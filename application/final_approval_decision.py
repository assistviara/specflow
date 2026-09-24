"""Receive an explicit Human selection; do not record approval or route it."""
from dataclasses import dataclass
from enum import Enum

from application.final_approval_target import FinalApprovalTargetOutput
from application.review_result import ReviewResultOutput


class FinalApprovalDecision(str, Enum):
    FINAL_APPROVAL = 'Final Approval'
    IMPLEMENTATION_CORRECTION = 'Implementation Correction'
    PLAN_REVISION = 'Plan Revision'
    SPECIFICATION_RECONSIDERATION = 'Specification Reconsideration'
    CANCELLATION = 'Cancellation'


@dataclass(frozen=True)
class FinalApprovalDecisionInput:
    target: FinalApprovalTargetOutput
    # Supplied by the Human-facing caller, never derived from Review or AI output.
    human_decision: FinalApprovalDecision | str | None = None


@dataclass(frozen=True)
class DecisionFailure:
    code: str
    detail: str


@dataclass(frozen=True)
class FinalApprovalDecisionOutput:
    request: FinalApprovalDecisionInput
    decision: FinalApprovalDecision | None = None
    failures: tuple[DecisionFailure, ...] = ()

    @property
    def is_final_approval(self) -> bool:
        """Identifies the selection only; this is not Approval Validation."""
        return not self.failures and self.decision is FinalApprovalDecision.FINAL_APPROVAL

    @property
    def review(self) -> ReviewResultOutput:
        """Existing report, result and Review Input for Human inspection.

        The unchanged target also exposes its path, hash, branch, commits and
        Evidence/Diff/Report references. No new presentation snapshot is built.
        """
        return self.request.target.request.entry.request.handoff.request.continuation.request.review


class FinalApprovalDecisionUseCase:
    def execute(self, request: FinalApprovalDecisionInput) -> FinalApprovalDecisionOutput:
        if not isinstance(request.target, FinalApprovalTargetOutput) or not request.target.succeeded:
            return FinalApprovalDecisionOutput(request, failures=(DecisionFailure(
                'TARGET_NOT_ESTABLISHED', 'A successful Target 2 output is required.'),))
        if request.human_decision is None:
            return FinalApprovalDecisionOutput(request)
        # Accept only this decision type or an exact selection label. In
        # particular, do not normalize Review/Approval enums or ambiguous text.
        if type(request.human_decision) not in (str, FinalApprovalDecision):
            return self._invalid(request)
        try:
            decision = FinalApprovalDecision(request.human_decision)
        except ValueError:
            return self._invalid(request)
        return FinalApprovalDecisionOutput(request, decision)

    @staticmethod
    def _invalid(request: FinalApprovalDecisionInput) -> FinalApprovalDecisionOutput:
        return FinalApprovalDecisionOutput(request, failures=(DecisionFailure(
            'EXPLICIT_DECISION_REQUIRED', 'Select one of the five explicit Human Final Approval decisions.'),))
