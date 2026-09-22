from application.review_result import ReviewResultOutput
from application.review_result_parser import parse_result_report, validate_result_report
from application.review_result_prompt import result_context, build_result_prompt
from application.review_findings import ASPECTS
from application.review_stages import STAGES, StagedReviewOutput
from core.ai.ai_service import AIService
from core.ai.prompt_adapter import PromptAdapter


def _review_failures(review: StagedReviewOutput) -> tuple[str, ...]:
    failures = []
    if review.prepared.review_input is None or review.prepared.missing_information:
        failures.append('Required Review Input unavailable')
    if review.mode == 'BATCH':
        batch = review.batch
        if batch is None:
            failures.append('BATCH review not performed')
        else:
            if tuple(a.aspect for a in batch.aspects) != ASPECTS:
                failures.append('Required BATCH aspects not established')
            if batch.execution_error:
                failures.append(f'BATCH execution: {batch.execution_error}')
            if batch.parse_error:
                failures.append(f'BATCH parsing: {batch.parse_error}')
    elif review.mode == 'STAGED':
        if tuple(stage.stage for stage in review.stages) != STAGES[:4]:
            failures.append('Required individual stages not established')
        if review.integration is None or review.integration.stage != STAGES[4]:
            failures.append('Integration Review not established')
        for stage in (*review.stages, *((review.integration,) if review.integration else ())):
            if stage.execution_error:
                failures.append(f'{stage.stage} execution: {stage.execution_error}')
            if stage.parse_error:
                failures.append(f'{stage.stage} parsing: {stage.parse_error}')
            if stage.assessment is None:
                failures.append(f'{stage.stage} assessment unavailable')
    else:
        failures.append('Unknown Review Mode')
    # Semantic uncertainty is a Review outcome, not a technical failure.
    return tuple(failures)


class ClassifyReviewResultUseCase:
    def __init__(self, ai_service: AIService) -> None:
        self._ai_service = ai_service

    def execute(self, review: StagedReviewOutput) -> ReviewResultOutput:
        failures = _review_failures(review)
        if failures:
            return ReviewResultOutput(review, review_failures=failures)
        context = result_context(review)
        try:
            response = self._ai_service.run(PromptAdapter.to_ai_request(build_result_prompt(context)))
        except Exception as error:
            return ReviewResultOutput(review, execution_error=f'{type(error).__name__}: {error}')
        if not response.success:
            return ReviewResultOutput(review, execution_error=response.error_message, raw_response=response.content)
        try:
            report = parse_result_report(response.content, context)
        except ValueError as error:
            return ReviewResultOutput(review, parse_error=str(error), raw_response=response.content)
        errors = validate_result_report(report, context)
        return ReviewResultOutput(review, None if errors else report.proposed_result, report,
                                  validation_errors=errors, raw_response=response.content)
