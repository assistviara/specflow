from dataclasses import dataclass

from application.review_findings import ReviewFinding, ReviewImplementationOutput
from application.review_input import PrepareReviewInputOutput

STAGES = ('Requirement Review', 'Change Scope Review', 'Implementation Review', 'Test Review', 'Integration Review')


@dataclass(frozen=True)
class StageAssessment:
    checked: str
    findings: tuple[ReviewFinding, ...]
    unconfirmed: tuple[str, ...]


@dataclass(frozen=True)
class StageExecution:
    stage: str
    context: dict
    assessment: StageAssessment | None = None
    execution_error: str | None = None
    parse_error: str | None = None
    raw_response: str | None = None

    @property
    def completed(self) -> bool:
        return (self.assessment is not None and not self.assessment.unconfirmed
                and not self.execution_error and not self.parse_error)


@dataclass(frozen=True)
class StagedReviewOutput:
    mode: str
    prepared: PrepareReviewInputOutput
    stages: tuple[StageExecution, ...] = ()
    integration: StageExecution | None = None
    batch: ReviewImplementationOutput | None = None

    @property
    def completed(self) -> bool:
        if self.mode == 'BATCH':
            return self.batch is not None and self.batch.completed
        return (len(self.stages) == 4 and all(stage.completed for stage in self.stages)
                and self.integration is not None and self.integration.completed)
