import json
from dataclasses import asdict
from pathlib import Path

from core.prompt_builder import PromptBuilder, PromptResult
from application.review_result_prompt import result_context


def correction_context(request, instructions) -> dict:
    context = result_context(request.review.review)
    context['result'] = asdict(request.review.report)
    context['routing'] = {
        'current_state': request.current_state,
        'control': asdict(request.control),
        'problems': [asdict(problem) for problem in request.problems],
    }
    context['instructions'] = [asdict(instruction) for instruction in instructions]
    return json.loads(json.dumps(context, default=str, ensure_ascii=False))


def build_correction_prompt(context: dict) -> PromptResult:
    path = Path(__file__).resolve().parent.parent / 'prompt_templates' / 'correction_instruction_prompt_template.md'
    return PromptBuilder().build(path.read_text(encoding='utf-8'), {
        'CORRECTION_INPUT': json.dumps(context, ensure_ascii=False),
    })
