import json
from dataclasses import asdict
from pathlib import Path

from core.prompt_builder import PromptBuilder
from core.ai.prompt_adapter import PromptAdapter


def build_cycle_prompt(original: str, context: dict) -> str:
    template = Path(__file__).resolve().parent.parent / 'prompt_templates' / 'correction_execution_prompt_template.md'
    result = PromptBuilder().build(template.read_text(encoding='utf-8'), {
        'IMPLEMENTATION_PROMPT': original,
        'CORRECTION_CONTEXT': json.dumps(context, default=str, ensure_ascii=False),
    })
    return PromptAdapter.to_ai_request(result).prompt


def history_context(history, tests) -> dict:
    data = json.loads(json.dumps(asdict(history), default=str, ensure_ascii=False))
    previous = history.routing.request.review
    return {
        'comparison_rule': 'Compare previous issues with current artifacts. History is read-only; do not copy old Findings into new Findings or invent approvals.',
        'previous_review': json.loads(json.dumps(asdict(previous), default=str, ensure_ascii=False)),
        'instructions': data['routing']['instructions'],
        'correction_history': data,
        'previous_evidence_id': str(history.previous_evidence_id),
        'new_evidence_id': str(history.new_evidence_id) if history.new_evidence_id else None,
        'correction_summary': [attempt.summary for attempt in history.attempts],
        'changed_files': list(history.changed_files),
        'retest_result': data['test_state'],
        'required_tests': asdict(tests),
    }
