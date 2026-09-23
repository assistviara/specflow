from dataclasses import dataclass
from enum import Enum

from application.correction_cycle import CorrectionHistory
from application.review_result import ReviewResultOutput
from application.review_retry import ReviewRetryHistory


class ContinuationDecision(str, Enum):
    CONTINUATION_ALLOWED = 'CONTINUATION_ALLOWED'
    CORRECTION_NOT_NEEDED = 'CORRECTION_NOT_NEEDED'
    STOPPED = 'STOPPED'
    UNDETERMINED = 'UNDETERMINED'


class EarlyStopCondition(str, Enum):
    REPEATED_ISSUE = 'REPEATED_ISSUE'
    PLAN_DEVIATION = 'PLAN_DEVIATION'
    UNREASONABLE_FILE_GROWTH = 'UNREASONABLE_FILE_GROWTH'
    TEST_REGRESSION = 'TEST_REGRESSION'
    TEST_DETERIORATION = 'TEST_DETERIORATION'
    NEW_TEST_EXECUTION_ERROR = 'NEW_TEST_EXECUTION_ERROR'
    NEW_ERROR_OR_MAJOR_WARNING = 'NEW_ERROR_OR_MAJOR_WARNING'
    UNSOLVABLE_WITHIN_PLAN = 'UNSOLVABLE_WITHIN_PLAN'
    SPECIFICATION_UNCERTAINTY = 'SPECIFICATION_UNCERTAINTY'
    PLAN_REVISION_REQUIRED = 'PLAN_REVISION_REQUIRED'
    ARCHITECTURE_DECISION_REQUIRED = 'ARCHITECTURE_DECISION_REQUIRED'
    SCOPE_VIOLATION = 'SCOPE_VIOLATION'
    CRITICAL_CHANGE = 'CRITICAL_CHANGE'
    UNSAFE_CAUSE_OR_IMPACT = 'UNSAFE_CAUSE_OR_IMPACT'
    NON_CONVERGENCE = 'NON_CONVERGENCE'
    SAFE_CONTINUATION = 'SAFE_CONTINUATION'


@dataclass(frozen=True)
class ExistingAssessment:
    """Explicit projection of an existing Review/diagnosis, never a new evaluation.

    SAFE_CONTINUATION confirms that necessary comparisons are sufficient and
    correction remains safe in scope. Absence of findings is not this assessment.
    References are paths into ContinuationInput (review/history), not free URLs.
    None preserves a question which the existing artifacts have not settled.
    """
    condition: EarlyStopCondition
    established: bool | None
    rationale: str
    references: tuple[str, ...]


@dataclass(frozen=True)
class TestCorrespondence:
    """Existing confirmation that a target/full test set is comparable across cycles.

    Identical commands alone do not establish correspondence. Initial expected
    failures are intentionally excluded from the post-implementation comparison.
    """
    phase: str
    confirmed: bool | None
    rationale: str
    references: tuple[str, ...]


@dataclass(frozen=True)
class ContinuationReason:
    code: str
    rationale: str
    references: tuple[str, ...]


@dataclass(frozen=True)
class ContinuationInput:
    review: ReviewResultOutput
    correction_count: int | None
    history: tuple[CorrectionHistory, ...] = ()
    assessments: tuple[ExistingAssessment, ...] = ()
    retry_history: tuple[ReviewRetryHistory, ...] = ()
    test_correspondences: tuple[TestCorrespondence, ...] = ()


@dataclass(frozen=True)
class ContinuationOutput:
    # Retain the original objects, including diagnostics, failures and provenance.
    request: ContinuationInput
    decision: ContinuationDecision
    reasons: tuple[ContinuationReason, ...]
