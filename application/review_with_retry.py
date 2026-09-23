from collections.abc import Callable
from dataclasses import dataclass
from uuid import uuid4

from application.classify_review_result import ClassifyReviewResultUseCase
from application.review_input import PrepareReviewInputOutput
from application.review_result import ReviewResultOutput
from application.review_retry import ReviewAIOperation, ReviewOperationKind, RetryAuthorization, AIExecutionAttempt, ReviewRetryHistory
from application.review_stages import StagedReviewOutput
from application.semantic_staged_review import SemanticStagedReviewUseCase
from application.technical_review_retry import TechnicalReviewRetryUseCase
from core.ai.ai_request import AIRequest
from core.ai.ai_response import AIResponse
from core.ai.ai_service import AIService


@dataclass(frozen=True)
class ReviewRetryOutput:
    """Keep attempt history alongside the original Review/Finding references."""

    review: StagedReviewOutput
    history: tuple[ReviewRetryHistory, ...]
    classification: ReviewResultOutput | None = None

    @property
    def recovery_failed(self) -> bool:
        return any(item.recovery_failed for item in self.history)


class _RetryingReviewService:
    def __init__(self, retry, kinds, context):
        self._retry = retry
        self._kinds = iter(kinds)
        self._context = context
        self.history = []

    def run(self, request: AIRequest) -> AIResponse:
        operation = ReviewAIOperation(uuid4(), next(self._kinds), request, self._context)
        history = self._retry.execute(operation)
        self.history.append(history)
        attempt = history.final_attempt
        if attempt.response is not None:
            return attempt.response
        return AIResponse('', False, attempt.execution_error)


class ReviewWithRetryUseCase:
    def __init__(self, ai_service: AIService, authorize: Callable[[ReviewAIOperation, AIExecutionAttempt], RetryAuthorization]) -> None:
        self._retry = TechnicalReviewRetryUseCase(ai_service, authorize)

    def execute(self, prepared: PrepareReviewInputOutput, *, mode: str) -> ReviewRetryOutput:
        if mode not in ('BATCH', 'STAGED'):
            raise ValueError('Explicit BATCH or STAGED mode is required')
        kinds = (ReviewOperationKind.BATCH,) if mode == 'BATCH' else (
            ReviewOperationKind.REQUIREMENT, ReviewOperationKind.CHANGE_SCOPE,
            ReviewOperationKind.IMPLEMENTATION, ReviewOperationKind.TEST, ReviewOperationKind.INTEGRATION,
        )
        service = _RetryingReviewService(self._retry, kinds, prepared)
        review = SemanticStagedReviewUseCase(service).execute(prepared, mode=mode, stop_on_execution_error=True)
        return ReviewRetryOutput(review, tuple(service.history))

    def classify(self, reviewed: ReviewRetryOutput | StagedReviewOutput) -> ReviewRetryOutput:
        if isinstance(reviewed, ReviewRetryOutput) and reviewed.classification is not None:
            return reviewed
        review = reviewed.review if isinstance(reviewed, ReviewRetryOutput) else reviewed
        prior_history = reviewed.history if isinstance(reviewed, ReviewRetryOutput) else ()
        service = _RetryingReviewService(self._retry, (ReviewOperationKind.RESULT_CLASSIFICATION,), review)
        classification = ClassifyReviewResultUseCase(service).execute(review)
        return ReviewRetryOutput(review, (*prior_history, *service.history), classification)
