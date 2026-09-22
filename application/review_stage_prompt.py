import json
from dataclasses import asdict
from pathlib import Path

from application.review_prompt_builder import review_context
from application.review_input import PrepareReviewInputOutput
from application.review_stages import StageExecution
from core.prompt_builder import PromptBuilder, PromptResult


def mechanical_context(prepared: PrepareReviewInputOutput) -> dict:
    data = review_context(prepared)
    request = data['acquired']['request']
    return {key: data[key] for key in ('missing_information', 'acquisition_errors', 'mismatches')} | {
        key: request[key] for key in ('collection_missing_evidence', 'collection_inconsistencies', 'collection_human_approval_required')
    }


def individual_context(prepared: PrepareReviewInputOutput, stage: str) -> dict:
    data = review_context(prepared)['review_input']
    fields = {
        'Requirement Review': ('specification', 'implementation_plan', 'evidence'),
        'Change Scope Review': ('specification', 'implementation_plan', 'codex_prompt', 'evidence', 'repository_state', 'approval_records'),
        'Implementation Review': ('specification', 'implementation_plan', 'sources', 'repository_state', 'evidence'),
        'Test Review': ('specification', 'implementation_plan', 'tests', 'sources', 'test_state', 'repository_state', 'evidence'),
    }[stage]
    selected = {field: data[field] for field in fields}
    evidence_fields = {
        'Requirement Review': ('identity', 'basis', 'scope', 'changes', 'deviations'),
        'Change Scope Review': ('identity', 'basis', 'scope', 'changes', 'deviations'),
        'Implementation Review': ('identity', 'basis', 'scope', 'changes', 'deviations', 'codex_summary'),
        'Test Review': ('identity', 'basis', 'verification', 'deviations', 'codex_summary'),
    }[stage]
    selected['evidence'] = {key: data['evidence'][key] for key in evidence_fields}
    if stage in ('Implementation Review', 'Test Review'):
        selected['repository_state'] = {
            key: data['repository_state'][key]
            for key in ('branch', 'base_commit', 'git_diff', 'created_files', 'modified_files', 'deleted_files', 'unavailable_evidence')
        }
    return {'stage': stage, 'input': selected, 'mechanical': mechanical_context(prepared)}


def _resolve(reference: str, context: dict):
    value = context
    for part in reference.split('.'):
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def integration_context(prepared: PrepareReviewInputOutput, stages: tuple[StageExecution, ...]) -> dict:
    results = []
    for stage in stages:
        result = json.loads(json.dumps(asdict(stage), ensure_ascii=False))
        result.pop('context')
        # Pass cited evidence, not every individual Stage's full input again.
        result['grounds'] = [
            [{'reference': ref, 'value': _resolve(ref, stage.context)} for ref in finding.references]
            for finding in stage.assessment.findings
        ] if stage.assessment is not None else []
        results.append(result)
    return {'stage': 'Integration Review', 'stages': results, 'mechanical': mechanical_context(prepared)}


def build_stage_prompt(context: dict) -> PromptResult:
    path = Path(__file__).resolve().parent.parent / 'prompt_templates' / 'review_stage_prompt_template.md'
    return PromptBuilder().build(path.read_text(encoding='utf-8'), {'STAGE_INPUT': json.dumps(context, ensure_ascii=False)})
