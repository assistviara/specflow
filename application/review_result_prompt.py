import json
from dataclasses import asdict
from pathlib import Path
from core.prompt_builder import PromptBuilder
from core.prompt_builder import PromptResult
from application.review_stages import StagedReviewOutput


def result_context(review: StagedReviewOutput) -> dict:
    data = json.loads(json.dumps(asdict(review), default=str, ensure_ascii=False))
    concerns = []

    def collect(items, path):
        concerns.extend(f'{path}.{index}' for index in range(len(items)))

    prepared = data['prepared']
    collect(prepared['mismatches'], 'review.prepared.mismatches')
    request = prepared['acquired']['request']
    for key in ('collection_missing_evidence', 'collection_inconsistencies', 'collection_human_approval_required'):
        collect(request[key], f'review.prepared.acquired.request.{key}')
    if prepared['review_input'] is not None:
        evidence = prepared['review_input']['evidence']
        for key, items in evidence['deviations'].items():
            collect(items, f'review.prepared.review_input.evidence.deviations.{key}')

    def assessment(value, path):
        if value is not None:
            for field in ('findings', 'unconfirmed'):
                collect(value[field], f'{path}.{field}')

    if data['mode'] == 'BATCH' and data['batch'] is not None:
        for index, item in enumerate(data['batch']['aspects']):
            assessment(item, f'review.batch.aspects.{index}')
    elif data['mode'] == 'STAGED':
        for index, stage in enumerate(data['stages']):
            assessment(stage['assessment'], f'review.stages.{index}.assessment')
        if data['integration'] is not None:
            assessment(data['integration']['assessment'], 'review.integration.assessment')
    return {'review': data, 'concerns': concerns}


def build_result_prompt(context: dict) -> PromptResult:
    path = Path(__file__).resolve().parent.parent / 'prompt_templates' / 'review_result_prompt_template.md'
    return PromptBuilder().build(path.read_text(encoding='utf-8'), {'RESULT_INPUT': json.dumps(context, ensure_ascii=False)})
