from dataclasses import dataclass
from enum import Enum
from application.review_stages import StagedReviewOutput


class ReviewResult(str, Enum):
    APPROVED = 'APPROVED'
    REVISION_REQUIRED = 'REVISION_REQUIRED'
    HUMAN_REVIEW_REQUIRED = 'HUMAN_REVIEW_REQUIRED'


@dataclass(frozen=True)
class ReviewResultReport:
    proposed_result: ReviewResult
    rationale: str
    references: tuple[str, ...]
    checks: dict
    resolutions: tuple[dict, ...]
    problem: str
    cause: str
    targets: tuple[str, ...]
    safe_scope_reason: str
    human_questions: tuple[str, ...]
    unresolved: tuple[str, ...]


@dataclass(frozen=True)
class ReviewResultOutput:
    review: StagedReviewOutput
    result: ReviewResult | None = None
    report: ReviewResultReport | None = None
    review_failures: tuple[str, ...] = ()
    validation_errors: tuple[str, ...] = ()
    execution_error: str | None = None
    parse_error: str | None = None
    raw_response: str | None = None
