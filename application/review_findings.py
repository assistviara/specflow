from dataclasses import dataclass
from application.review_input import PrepareReviewInputOutput

ASPECTS = ('Requirement', 'Scope', 'Implementation', 'Test', 'Evidence')


@dataclass(frozen=True)
class ReviewFinding:
    aspect: str
    description: str
    rationale: str
    references: tuple[str, ...]
    origin: str


@dataclass(frozen=True)
class AspectReview:
    aspect: str
    checked: str
    findings: tuple[ReviewFinding, ...]
    unconfirmed: tuple[str, ...]


@dataclass(frozen=True)
class ReviewImplementationOutput:
    prepared: PrepareReviewInputOutput
    aspects: tuple[AspectReview, ...] = ()
    execution_error: str | None = None
    parse_error: str | None = None
    raw_response: str | None = None

    @property
    def completed(self) -> bool:
        return (self.prepared.review_input is not None and len(self.aspects) == 5
                and not self.execution_error and not self.parse_error
                and not any(a.unconfirmed for a in self.aspects))
