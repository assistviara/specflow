from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from application.correction_continuation import ContinuationOutput
from application.correction_cycle import CorrectionCycleOutput


class HandoffType(str, Enum):
    HUMAN_REVIEW = 'HUMAN_REVIEW'
    CRITICAL_CHANGE_APPROVAL = 'CRITICAL_CHANGE_APPROVAL'
    PHASE_6 = 'PHASE_6'
    NONE = 'NONE'


@dataclass(frozen=True)
class CriticalChangeReferences:
    """References to change facts already explicitly established upstream."""
    content_reference: str
    reason_reference: str
    targets_reference: str
    impact_reference: str


@dataclass(frozen=True)
class ExistingIssueResolution:
    """Projection of an explicit existing resolution, not a new Human/AI decision.

    The caller identifies the retained historical/cycle issue and the current
    Review content that already resolves it. Target 9 validates the references;
    it does not infer resolution from APPROVED or from issue counts.
    """
    issue_reference: str
    resolution_reference: str


@dataclass(frozen=True)
class ReviewHandoffInput:
    continuation: ContinuationOutput | None
    implementation_id: UUID | None
    current_state: str | None
    # Paths into this input's acquired object graph; no filesystem re-acquisition.
    required_references: tuple[str, ...] = ()
    cycle: CorrectionCycleOutput | None = None
    critical_change: CriticalChangeReferences | None = None
    unresolved_references: tuple[str, ...] = ()
    resolutions: tuple[ExistingIssueResolution, ...] = ()


@dataclass(frozen=True)
class HandoffDiagnostic:
    code: str
    detail: str
    references: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReviewHandoffOutput:
    request: ReviewHandoffInput
    handoff_type: HandoffType
    reason: tuple[str, ...]
    required_human_action: tuple[str, ...] = ()
    unresolved_issues: tuple[str, ...] = ()
    artifact_references: tuple[str, ...] = ()
    failures: tuple[HandoffDiagnostic, ...] = ()

    @property
    def current_state(self) -> str | None:
        return self.request.current_state

    @property
    def human_judgment_required(self) -> bool:
        return not self.failures and self.handoff_type in (HandoffType.HUMAN_REVIEW, HandoffType.CRITICAL_CHANGE_APPROVAL)
