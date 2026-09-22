from application.review_findings import ReviewImplementationOutput
from application.review_findings_parser import parse_review_findings
from application.review_prompt_builder import build_review_prompt, review_context
from core.ai.prompt_adapter import PromptAdapter
from core.ai.ai_service import AIService
from application.review_input import PrepareReviewInputOutput


class ReviewImplementationUseCase:
    def __init__(self, ai_service: AIService) -> None:
        self._ai_service = ai_service

    def execute(self, prepared: PrepareReviewInputOutput) -> ReviewImplementationOutput:
        if prepared.review_input is None:
            return ReviewImplementationOutput(prepared)
        try:
            request = PromptAdapter.to_ai_request(build_review_prompt(prepared))
            response = self._ai_service.run(request)
        except Exception as error:
            return ReviewImplementationOutput(prepared, execution_error=f'{type(error).__name__}: {error}')
        if not response.success:
            return ReviewImplementationOutput(prepared, execution_error=response.error_message, raw_response=response.content)
        try:
            aspects = parse_review_findings(response.content, review_context(prepared))
        except ValueError as error:
            return ReviewImplementationOutput(prepared, parse_error=str(error), raw_response=response.content)
        return ReviewImplementationOutput(prepared, aspects, raw_response=response.content)
