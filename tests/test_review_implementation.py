import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

from test_prepare_review_input import review_case
from core.ai.ai_response import AIResponse
from core.ai.ai_service import AIService


def response():
    return {'aspects': [dict(aspect=a, checked='Compared requirements and current artifacts', findings=[], unconfirmed=[])
                        for a in ('Requirement', 'Scope', 'Implementation', 'Test', 'Evidence')]}


def test_reviews_five_aspects_preserving_input_mismatch_and_semantic_findings_without_final_result(review_case):
    from application.review_implementation import ReviewImplementationUseCase
    c = review_case
    c['test_provider'].get_state.return_value = replace(c['actual'], full_test_result='FAIL')
    prepared = c['use_case'].execute(c['request'])
    payload = response()
    for index, description in ((0, 'Required processing is missing'), (3, 'Required behavior is not tested')):
        payload['aspects'][index]['findings'] = [dict(description=description, rationale='Required behavior differs from current code', references=['review_input.specification.content', 'review_input.sources.0.content'])]
    runner = Mock()
    runner.run.return_value = AIResponse(json.dumps(payload), True)
    before = {p: p.read_bytes() for p in c['request'].repository_path.iterdir() if p.is_file()}
    output = ReviewImplementationUseCase(AIService(runner)).execute(prepared)
    assert output.completed
    assert len(output.aspects) == 5
    assert len(output.aspects[0].findings) == 1
    assert output.aspects[0].findings[0].origin == 'semantic'
    assert output.prepared is prepared
    assert output.prepared.mismatches == prepared.mismatches
    assert 'value = 1' in runner.run.call_args.args[0].prompt
    assert 'test.full_test_result' in runner.run.call_args.args[0].prompt
    assert not hasattr(output, 'review_result')
    assert before == {p: p.read_bytes() for p in before}
    runner.run.assert_called_once()

import pytest


def execute(c, payload=None, response_override=None):
    from application.review_implementation import ReviewImplementationUseCase
    runner = Mock()
    runner.run.return_value = response_override or AIResponse(json.dumps(payload or response()), True)
    prepared = c['use_case'].execute(c['request'])
    return ReviewImplementationUseCase(AIService(runner)).execute(prepared), runner


def test_invalid_input_does_not_call_ai(review_case):
    review_case['evidence'].basis.specification_path.unlink()
    output, runner = execute(review_case)
    assert not output.completed
    assert output.prepared.missing_information
    assert output.aspects == ()
    runner.run.assert_not_called()


@pytest.mark.parametrize('aspect', range(5))
def test_each_aspect_retains_findings_and_unconfirmed_separately(review_case, aspect):
    payload = response()
    payload['aspects'][aspect]['findings'] = [dict(description='Missing or extra implementation', rationale='Compared approved requirement', references=['review_input.implementation_plan.content'])]
    payload['aspects'][aspect]['unconfirmed'] = ['Insufficient selected context to confirm cause']
    output, _ = execute(review_case, payload)
    assert not output.completed
    assert output.aspects[aspect].findings[0].rationale
    assert output.aspects[aspect].unconfirmed
    assert output.execution_error is None
    assert output.parse_error is None


def test_empty_findings_do_not_erase_mechanical_mismatch(review_case):
    review_case['test_provider'].get_state.return_value = replace(review_case['actual'], full_test_result='FAIL')
    output, _ = execute(review_case)
    assert output.completed
    assert all(not a.findings for a in output.aspects)
    assert output.prepared.mismatches


@pytest.mark.parametrize('failure', ['reported', 'exception'])
def test_ai_failure_is_not_review_finding(review_case, failure):
    from application.review_implementation import ReviewImplementationUseCase
    runner = Mock()
    if failure == 'reported':
        runner.run.return_value = AIResponse('', False, 'AI unavailable')
    else:
        runner.run.side_effect = RuntimeError('AI unavailable')
    prepared = review_case['use_case'].execute(review_case['request'])
    output = ReviewImplementationUseCase(AIService(runner)).execute(prepared)
    assert not output.completed
    assert output.execution_error
    assert output.parse_error is None
    assert output.aspects == ()
    assert output.prepared is prepared
    runner.run.assert_called_once()


@pytest.mark.parametrize('mutation', ['missing_aspect', 'duplicate_aspect', 'empty_checked', 'missing_reference', 'invalid_reference', 'extra_result', 'extra_severity', 'wrong_type'])
def test_invalid_response_is_not_empty_success(review_case, mutation):
    payload = response()
    finding = dict(description='Issue', rationale='Reason', references=['review_input.sources.0.content'])
    payload['aspects'][0]['findings'] = [finding]
    if mutation == 'missing_aspect':
        payload['aspects'].pop()
    elif mutation == 'duplicate_aspect':
        payload['aspects'][1]['aspect'] = 'Requirement'
    elif mutation == 'empty_checked':
        payload['aspects'][0]['checked'] = ''
    elif mutation == 'missing_reference':
        finding['references'] = []
    elif mutation == 'invalid_reference':
        finding['references'] = ['review_input.sources.99.content']
    elif mutation == 'extra_result':
        payload['result'] = 'some decision'
    elif mutation == 'extra_severity':
        finding['severity'] = 'high'
    else:
        payload['aspects'][0]['unconfirmed'] = 'not an array'
    output, _ = execute(review_case, payload)
    assert not output.completed
    assert output.parse_error
    assert output.execution_error is None
    assert output.aspects == ()
    assert output.raw_response == json.dumps(payload)


def test_non_json_response_is_parse_failure(review_case):
    output, _ = execute(review_case, response_override=AIResponse('not JSON', True))
    assert output.parse_error
    assert not output.completed


@pytest.mark.parametrize('status,result', [('COMPLETED', 'FAIL'), ('ERROR', 'NONE'), ('NOT_RUN', 'NONE')])
def test_test_facts_are_not_ai_failures_or_final_decisions(review_case, status, result):
    c = review_case
    c['test_provider'].get_state.return_value = replace(c['actual'], target_test_status=status, target_test_result=result, errors=('test error detail',), warnings=('test warning',))
    c['repository'].load.return_value = replace(c['evidence'], deviations=replace(c['evidence'].deviations, unfinished_items=('unfinished work',), human_approval_required=('approval basis',)))
    output, runner = execute(c)
    prompt = runner.run.call_args.args[0].prompt
    for fact in ('test error detail', 'test warning', 'unfinished work', 'approval basis', 'initial_test_result', 'target_test_result'):
        assert fact in prompt
    assert output.completed
    assert output.execution_error is None
    assert output.prepared.review_input.test_state.target_test_result == result


@pytest.mark.parametrize('aspect,description,reference', [
    (0, 'Required validation is absent', 'review_input.specification.content'),
    (1, 'Unrequested feature added', 'review_input.implementation_plan.content'),
    (1, 'Change exceeds Human Approval scope', 'review_input.approval_records.1.artifact_path'),
    (2, 'Unnecessary existing source behavior change', 'review_input.sources.0.content'),
    (3, 'Required behavior lacks assertions', 'review_input.tests.0.content'),
    (4, 'Evidence does not reflect current result', 'review_input.test_state.full_test_result'),
])
def test_grounded_issue_categories_are_retained_without_routing(review_case, aspect, description, reference):
    payload = response()
    payload['aspects'][aspect]['findings'] = [dict(description=description, rationale='Comparison with the referenced artifact', references=[reference])]
    output, _ = execute(review_case, payload)
    finding = output.aspects[aspect].findings[0]
    assert finding.description == description
    assert finding.references == (reference,)
    assert finding.aspect == payload['aspects'][aspect]['aspect']
    assert finding.origin == 'semantic'
    assert output.completed


def test_prompt_preserves_saved_actual_and_collection_sources(review_case):
    from application.review_prompt_builder import build_review_prompt
    c = review_case
    c['request'] = replace(c['request'], collection_missing_evidence=('report unavailable',), collection_inconsistencies=('reported file mismatch',), collection_human_approval_required=('scope approval needed',))
    c['test_provider'].get_state.return_value = replace(c['actual'], full_test_result='FAIL')
    prepared = c['use_case'].execute(c['request'])
    prompt = build_review_prompt(prepared)
    assert prompt.is_ready
    context = json.loads(prompt.content.split('# Review Input\n', 1)[1])
    assert context['review_input']['evidence']['verification']['full_test_result'] == 'PASS'
    assert context['review_input']['test_state']['full_test_result'] == 'FAIL'
    assert context['review_input']['request']['collection_missing_evidence'] == ['report unavailable']
    assert context['review_input']['request']['collection_human_approval_required'] == ['scope approval needed']
    assert context['mismatches']
    assert context['review_input']['tests'][0]['content'] == 'assert value == 1\n'


@pytest.mark.parametrize('content', ['[]', 'null', '{"aspects": [], "aspects": []}', '{"aspects": [null]}'])
def test_malformed_response_retains_raw_text_and_original_diagnostics(review_case, content):
    output, runner = execute(review_case, response_override=AIResponse(content, True))
    assert output.parse_error
    assert output.raw_response == content
    assert output.aspects == ()
    assert not output.completed
    runner.run.assert_called_once()


def test_semantic_response_cannot_claim_mechanical_provenance(review_case):
    payload = response()
    payload['aspects'][0]['findings'] = [dict(description='Issue', rationale='Reason', references=['review_input.specification.content'], origin='mechanical')]
    output, _ = execute(review_case, payload)
    assert output.parse_error
    assert output.aspects == ()


def test_unconfirmed_without_findings_is_not_completed(review_case):
    payload = response()
    payload['aspects'][0]['unconfirmed'] = ['Requirement is ambiguous']
    output, _ = execute(review_case, payload)
    assert not output.completed
    assert all(not aspect.findings for aspect in output.aspects)
    assert output.aspects[0].unconfirmed == ('Requirement is ambiguous',)
    assert not output.parse_error
