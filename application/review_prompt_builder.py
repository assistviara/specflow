import json
from dataclasses import asdict
from pathlib import Path
from core.prompt_builder import PromptBuilder
from core.prompt_builder import PromptResult
from application.review_input import PrepareReviewInputOutput


def review_context(prepared: PrepareReviewInputOutput) -> dict:
    return json.loads(json.dumps(asdict(prepared), default=str, ensure_ascii=False))


def build_review_prompt(prepared: PrepareReviewInputOutput) -> PromptResult:
    template = (Path(__file__).resolve().parent.parent / 'prompt_templates' / 'review_prompt_template.md').read_text(encoding='utf-8')
    return PromptBuilder().build(template, {'REVIEW_INPUT': json.dumps(review_context(prepared), ensure_ascii=False)})
