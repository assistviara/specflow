from collections.abc import Callable

from application.review_retry import ReviewAIOperation, ReviewOperationKind, RetryAuthorization, AIExecutionAttempt, ReviewRetryHistory
from core.ai.ai_service import AIService


class TechnicalReviewRetryUseCase:
    """Execute a Phase 5 AI operation; retry only with explicit safety evidence.

    The caller verifies transient failure and unchanged artifacts/conditions.
    Failure text alone is never used to infer eligibility.
    """

    def __init__(self, ai_service: AIService, authorize: Callable[[ReviewAIOperation, AIExecutionAttempt], RetryAuthorization]) -> None:
        self._ai_service = ai_service
        self._authorize = authorize
        self._history = {}
        self._in_flight = set()

    def _attempt(self, operation: ReviewAIOperation) -> AIExecutionAttempt:
        try:
            return AIExecutionAttempt(response=self._ai_service.run(operation.request))
        except Exception as error:
            return AIExecutionAttempt(execution_error=f'{type(error).__name__}: {error}')

    def execute(self, operation: ReviewAIOperation) -> ReviewRetryHistory:
        if not isinstance(operation.kind, ReviewOperationKind):
            raise ValueError('Only the seven Phase 5 AI operations are supported')
        if operation.operation_id in self._history:
            history = self._history[operation.operation_id]
            if history.operation != operation:
                raise ValueError('Operation identity cannot be reused with changed inputs')
            return history
        if operation.operation_id in self._in_flight:
            raise ValueError('Operation is already executing')
        self._in_flight.add(operation.operation_id)
        try:
            history = self._execute_once(operation)
            self._history[operation.operation_id] = history
            return history
        finally:
            self._in_flight.remove(operation.operation_id)

    def _execute_once(self, operation: ReviewAIOperation) -> ReviewRetryHistory:
        original = self._attempt(operation)
        if original.succeeded:
            return ReviewRetryHistory(operation, original)
        try:
            authorization = self._authorize(operation, original)
            if not isinstance(authorization, RetryAuthorization):
                raise ValueError('Explicit RetryAuthorization is required')
        except Exception as error:
            return ReviewRetryHistory(operation, original, decision_error=f'{type(error).__name__}: {error}')
        permitted = (
            authorization.temporary_ai_failure is True
            and authorization.same_request_safe is True
            and authorization.artifacts_unchanged is True
            and authorization.conditions_unchanged is True
            and authorization.changes_required is False
            and isinstance(authorization.reason, str) and bool(authorization.reason.strip())
        )
        if not permitted:
            return ReviewRetryHistory(operation, original, authorization=authorization)
        retry = self._attempt(operation)
        return ReviewRetryHistory(operation, original, retry, authorization)
