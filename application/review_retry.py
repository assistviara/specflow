from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from application.review_input import PrepareReviewInputOutput
from application.review_stages import StagedReviewOutput
from core.ai.ai_request import AIRequest
from core.ai.ai_response import AIResponse


class ReviewOperationKind(str, Enum):
    BATCH = 'BATCH Review'
    REQUIREMENT = 'Requirement Review'
    CHANGE_SCOPE = 'Change Scope Review'
    IMPLEMENTATION = 'Implementation Review'
    TEST = 'Test Review'
    INTEGRATION = 'Integration Review'
    RESULT_CLASSIFICATION = 'Review Result Classification'


@dataclass(frozen=True)
class ReviewAIOperation:
    operation_id: UUID
    kind: ReviewOperationKind
    request: AIRequest
    context: PrepareReviewInputOutput | StagedReviewOutput


@dataclass(frozen=True)
class RetryAuthorization:
    temporary_ai_failure: bool = False
    same_request_safe: bool = False
    artifacts_unchanged: bool = False
    conditions_unchanged: bool = False
    changes_required: bool = True
    reason: str = ''


@dataclass(frozen=True)
class AIExecutionAttempt:
    response: AIResponse | None = None
    execution_error: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.response is not None and self.response.success and self.execution_error is None


@dataclass(frozen=True)
class ReviewRetryHistory:
    operation: ReviewAIOperation
    original: AIExecutionAttempt
    retry: AIExecutionAttempt | None = None
    authorization: RetryAuthorization | None = None
    decision_error: str | None = None

    @property
    def retry_count(self) -> int:
        return int(self.retry is not None)

    @property
    def recovered(self) -> bool:
        return self.retry is not None and self.retry.succeeded

    @property
    def recovery_failed(self) -> bool:
        return self.retry is not None and not self.retry.succeeded

    @property
    def final_attempt(self) -> AIExecutionAttempt:
        return self.retry if self.retry is not None else self.original
