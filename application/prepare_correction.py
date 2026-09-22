from application.correction_routing import (
    CorrectionInstruction, CorrectionRoutingInput, CorrectionRoutingOutput,
)
from application.correction_prompt import correction_context, build_correction_prompt
from application.correction_instruction_parser import parse_correction_instructions, validate_correction_instructions
from application.correction_validation import validate_routing
from core.ai.ai_service import AIService
from core.ai.prompt_adapter import PromptAdapter


def _instructions(request):
    report = request.review.report
    evidence = request.review.review.prepared.review_input.evidence
    groups = {}
    for index, problem in enumerate(request.problems):
        key = (problem.destination, problem.scope_reference,
               ('confirmed', problem.safe_group) if problem.safe_group else ('single', index))
        groups.setdefault(key, []).append(problem)
    instructions = []
    for problems in groups.values():
        first = problems[0]
        def collect(field):
            return tuple(value for problem in problems for value in getattr(problem, field))
        instructions.append(CorrectionInstruction(
            first.destination, report.problem, report.cause, collect('targets'), report.rationale,
            'result', collect('finding_references'), (
                *report.references,
                'review.prepared.review_input.specification',
                'review.prepared.review_input.implementation_plan',
                'review.prepared.review_input.evidence',
            ),
            first.scope_reference, evidence.scope.allowed_changes, evidence.scope.forbidden_changes,
            tuple(p.safe_scope_reason for p in problems), collect('required_test_references'), collect('correction_references'),
        ))
    return tuple(instructions)


class PrepareCorrectionUseCase:
    def __init__(self, ai_service: AIService) -> None:
        self._ai_service = ai_service

    def execute(self, request: CorrectionRoutingInput) -> CorrectionRoutingOutput:
        errors = validate_routing(request)
        if errors:
            return CorrectionRoutingOutput(request, blocked_reasons=errors)
        instructions = _instructions(request)
        context = correction_context(request, instructions)
        try:
            response = self._ai_service.run(PromptAdapter.to_ai_request(build_correction_prompt(context)))
        except Exception as error:
            return CorrectionRoutingOutput(request, execution_error=f'{type(error).__name__}: {error}')
        if not response.success:
            return CorrectionRoutingOutput(request, execution_error=response.error_message or 'AI execution failed', raw_response=response.content)
        try:
            items = parse_correction_instructions(response.content)
        except ValueError as error:
            return CorrectionRoutingOutput(request, parse_error=str(error), raw_response=response.content)
        errors = validate_correction_instructions(items, context['instructions'])
        return CorrectionRoutingOutput(request, () if errors else instructions,
                                       validation_errors=errors, raw_response=response.content)
