from application.review_implementation import ReviewImplementationUseCase
from application.review_stages import STAGES, StageExecution, StagedReviewOutput
from application.review_stage_parser import parse_stage_response
from application.review_stage_prompt import individual_context, integration_context, build_stage_prompt
from application.review_input import PrepareReviewInputOutput
from core.ai.ai_service import AIService
from core.ai.prompt_adapter import PromptAdapter


class SemanticStagedReviewUseCase:
    def __init__(self, ai_service: AIService) -> None:
        self._ai_service = ai_service
        self._batch = ReviewImplementationUseCase(ai_service)

    def execute(self, prepared: PrepareReviewInputOutput, *, mode: str, stop_on_execution_error: bool = False) -> StagedReviewOutput:
        if mode not in ('BATCH', 'STAGED'):
            raise ValueError('Explicit BATCH or STAGED mode is required')
        if mode == 'BATCH':
            return StagedReviewOutput(mode, prepared, batch=self._batch.execute(prepared))
        if prepared.review_input is None:
            return StagedReviewOutput(mode, prepared)
        completed_stages = []
        for stage in STAGES[:4]:
            execution = self._run(individual_context(prepared, stage))
            completed_stages.append(execution)
            # Target 5 stops after unrecovered AI execution, retaining prior results.
            # The default Target 3 execution contract remains unchanged.
            if stop_on_execution_error and execution.execution_error:
                return StagedReviewOutput(mode, prepared, tuple(completed_stages))
        stages = tuple(completed_stages)
        integration = self._run(integration_context(prepared, stages))
        return StagedReviewOutput(mode, prepared, stages, integration)

    def _run(self, context: dict) -> StageExecution:
        stage = context['stage']
        try:
            response = self._ai_service.run(PromptAdapter.to_ai_request(build_stage_prompt(context)))
        except Exception as error:
            return StageExecution(stage, context, execution_error=f'{type(error).__name__}: {error}')
        if not response.success:
            return StageExecution(stage, context, execution_error=response.error_message, raw_response=response.content)
        try:
            assessment = parse_stage_response(response.content, context)
        except ValueError as error:
            return StageExecution(stage, context, parse_error=str(error), raw_response=response.content)
        return StageExecution(stage, context, assessment, raw_response=response.content)
