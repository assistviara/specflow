import json
from dataclasses import replace
from unittest.mock import Mock

from core.ai.ai_response import AIResponse
from core.ai.ai_service import AIService
from test_prepare_review_input import review_case

STAGES = ('Requirement Review', 'Change Scope Review', 'Implementation Review', 'Test Review', 'Integration Review')


def answer(stage, findings=(), unconfirmed=()):
    return AIResponse(json.dumps(dict(stage=stage, checked='Compared the selected artifacts', findings=list(findings), unconfirmed=list(unconfirmed))), True)


def finding(aspect, description, references):
    return dict(aspect=aspect, description=description, rationale='Evidence for ' + description, references=references)


def context(request):
    return json.loads(request.prompt.split('# Stage Input\n', 1)[1])


def test_integration_preserves_individual_findings_and_detects_cross_stage_conflict_without_final_result(review_case):
    from application.semantic_staged_review import SemanticStagedReviewUseCase
    c = review_case
    c['test_provider'].get_state.return_value = replace(c['actual'], full_test_result='FAIL')
    prepared = c['use_case'].execute(c['request'])
    implementation = finding('Implementation', 'Required processing is absent', ['input.sources.0.content'])
    test = finding('Test', 'The processing is verified', ['input.tests.0.content'])
    conflict = finding('Implementation', 'Individual assessments conflict', ['stages.2.assessment.findings.0', 'stages.3.assessment.findings.0'])
    runner = Mock()
    runner.run.side_effect = [answer(STAGES[0]), answer(STAGES[1]), answer(STAGES[2], [implementation]), answer(STAGES[3], [test]), answer(STAGES[4], [conflict])]
    output = SemanticStagedReviewUseCase(AIService(runner)).execute(prepared, mode='STAGED')
    calls = [context(call.args[0]) for call in runner.run.call_args_list]
    assert [item['stage'] for item in calls] == list(STAGES)
    assert all('stages' not in item for item in calls[:4])
    assert len(calls[4]['stages']) == 4
    assert calls[4]['mechanical']['mismatches']
    assert calls[4]['stages'][2]['assessment']['findings'][0]['rationale'] == implementation['rationale']
    assert calls[4]['stages'][2]['grounds'][0][0]['value'] == 'value = 1\n'
    assert output.completed
    assert output.prepared is prepared
    assert output.stages[2].assessment.findings[0].description == implementation['description']
    assert output.stages[3].assessment.findings[0].description == test['description']
    assert output.integration.assessment.findings[0].references == tuple(conflict['references'])
    assert not hasattr(output, 'review_result')

import pytest


def run_staged(c, answers=None, mode='STAGED'):
    from application.semantic_staged_review import SemanticStagedReviewUseCase
    runner = Mock()
    runner.run.side_effect = answers or [answer(stage) for stage in STAGES]
    prepared = c['use_case'].execute(c['request'])
    return SemanticStagedReviewUseCase(AIService(runner)).execute(prepared, mode=mode), runner


def test_stage_contexts_select_responsibility_specific_artifacts(review_case):
    output, runner = run_staged(review_case)
    inputs = [context(call.args[0]) for call in runner.run.call_args_list]
    assert 'sources' not in inputs[0]['input']
    assert 'tests' not in inputs[0]['input']
    assert 'verification' not in inputs[0]['input']['evidence']
    assert 'codex_prompt' in inputs[1]['input']
    assert 'specification' in inputs[1]['input']
    assert 'sources' not in inputs[1]['input']
    assert 'tests' not in inputs[2]['input']
    assert inputs[2]['input']['sources'][0]['content'] == 'value = 1\n'
    assert 'git_status' not in inputs[2]['input']['repository_state']
    assert 'test_state' in inputs[3]['input']
    assert 'verification' in inputs[3]['input']['evidence']
    assert 'input' not in inputs[4]
    assert all('context' not in item for item in inputs[4]['stages'])
    assert output.completed


def test_batch_delegates_to_existing_target_two(review_case):
    from application.semantic_staged_review import SemanticStagedReviewUseCase
    from application.review_implementation import ReviewImplementationUseCase
    from unittest.mock import patch
    from test_review_implementation import response
    prepared = review_case['use_case'].execute(review_case['request'])
    runner = Mock()
    runner.run.return_value = AIResponse(json.dumps(response()), True)
    service = AIService(runner)
    real = ReviewImplementationUseCase(service).execute
    with patch.object(ReviewImplementationUseCase, 'execute', autospec=True, side_effect=lambda self, data: real(data)) as delegated:
        output = SemanticStagedReviewUseCase(service).execute(prepared, mode='BATCH')
    assert output.batch.completed
    assert output.batch.prepared is prepared
    assert output.stages == ()
    assert output.integration is None
    delegated.assert_called_once()
    runner.run.assert_called_once()
    assert '# Stage Input' not in runner.run.call_args.args[0].prompt


@pytest.mark.parametrize('mode', [None, '', 'AUTO', 'staged'])
def test_mode_is_never_inferred(review_case, mode):
    from application.semantic_staged_review import SemanticStagedReviewUseCase
    runner = Mock()
    prepared = review_case['use_case'].execute(review_case['request'])
    with pytest.raises(ValueError):
        SemanticStagedReviewUseCase(AIService(runner)).execute(prepared, mode=mode)
    runner.run.assert_not_called()


def test_missing_mode_is_not_defaulted(review_case):
    from application.semantic_staged_review import SemanticStagedReviewUseCase
    with pytest.raises(TypeError):
        SemanticStagedReviewUseCase(Mock()).execute(review_case['use_case'].execute(review_case['request']))


def test_unformed_input_preserves_diagnostics_without_stage_execution(review_case):
    review_case['evidence'].basis.specification_path.unlink()
    output, runner = run_staged(review_case)
    assert output.prepared.missing_information
    assert not output.completed
    assert output.stages == ()
    assert output.integration is None
    runner.run.assert_not_called()


@pytest.mark.parametrize('position', range(5))
@pytest.mark.parametrize('failure', ['exception', 'reported', 'parse', 'unconfirmed'])
def test_failed_or_unconfirmed_stage_is_not_empty_success(review_case, position, failure):
    answers = [answer(stage) for stage in STAGES]
    answers[position] = {
        'exception': RuntimeError('runner failure'),
        'reported': AIResponse('', False, 'runner failure'),
        'parse': AIResponse('invalid JSON', True),
        'unconfirmed': answer(STAGES[position], unconfirmed=['Cannot confirm required behavior']),
    }[failure]
    output, runner = run_staged(review_case, answers)
    assert runner.run.call_count == 5
    assert [context(call.args[0])['stage'] for call in runner.run.call_args_list] == list(STAGES)
    failed = (*output.stages, output.integration)[position]
    assert not output.completed
    assert not failed.completed
    if failure == 'unconfirmed':
        assert failed.assessment.unconfirmed
        assert failed.assessment.findings == ()
        assert failed.execution_error is None and failed.parse_error is None
    elif failure == 'parse':
        assert failed.parse_error
        assert failed.execution_error is None
        assert failed.raw_response == 'invalid JSON'
        assert failed.assessment is None
    else:
        assert failed.execution_error
        assert failed.parse_error is None
        assert failed.assessment is None
    if position < 4:
        integrated = context(runner.run.call_args_list[-1].args[0])['stages'][position]
        assert integrated['stage'] == STAGES[position]
        assert integrated['execution_error'] or integrated['parse_error'] or integrated['assessment']['unconfirmed']


def test_duplicate_findings_and_mechanical_diagnostics_survive_clean_integration(review_case):
    c = review_case
    c['test_provider'].get_state.return_value = replace(c['actual'], full_test_result='FAIL')
    c['request'] = replace(c['request'], collection_missing_evidence=('report unavailable',), collection_inconsistencies=('old mismatch',), collection_human_approval_required=('approval basis',))
    item = finding('Requirement', 'Missing behavior', ['input.specification.content'])
    answers = [answer(STAGES[0], [item, item]), *[answer(stage) for stage in STAGES[1:]]]
    before = {p: p.read_bytes() for p in c['request'].repository_path.iterdir() if p.is_file()}
    output, runner = run_staged(c, answers)
    assert len(output.stages[0].assessment.findings) == 2
    assert output.integration.assessment.findings == ()
    assert output.prepared.mismatches
    mechanical = context(runner.run.call_args_list[-1].args[0])['mechanical']
    assert mechanical['collection_inconsistencies'] == ['old mismatch']
    assert mechanical['collection_human_approval_required'] == ['approval basis']
    assert output.prepared.review_input.evidence.verification.full_test_result == 'PASS'
    assert output.prepared.review_input.test_state.full_test_result == 'FAIL'
    assert before == {p: p.read_bytes() for p in before}


@pytest.mark.parametrize('problem', ['wrong_stage', 'unknown_aspect', 'missing_checked', 'empty_checked', 'no_reference', 'unknown_reference', 'foreign_stage_reference', 'final_result', 'severity', 'origin', 'wrong_unconfirmed', 'duplicate_key', 'null'])
def test_invalid_stage_response_is_retained_as_parse_failure(review_case, problem):
    payload = dict(stage=STAGES[0], checked='Checked requirements', findings=[finding('Requirement', 'Missing behavior', ['input.specification.content'])], unconfirmed=[])
    if problem == 'wrong_stage':
        payload['stage'] = STAGES[1]
    elif problem == 'unknown_aspect':
        payload['findings'][0]['aspect'] = 'Integration'
    elif problem == 'missing_checked':
        del payload['checked']
    elif problem == 'empty_checked':
        payload['checked'] = ''
    elif problem == 'no_reference':
        payload['findings'][0]['references'] = []
    elif problem == 'unknown_reference':
        payload['findings'][0]['references'] = ['input.sources.0.content']
    elif problem == 'foreign_stage_reference':
        payload['findings'][0]['references'] = ['stages.0.assessment']
    elif problem == 'final_result':
        payload['review_result'] = 'not allowed'
    elif problem == 'severity':
        payload['findings'][0]['severity'] = 'high'
    elif problem == 'origin':
        payload['findings'][0]['origin'] = 'mechanical'
    elif problem == 'wrong_unconfirmed':
        payload['unconfirmed'] = 'unknown'
    content = json.dumps(payload)
    if problem == 'duplicate_key':
        content = '{"stage": "x", "stage": "y"}'
    elif problem == 'null':
        content = 'null'
    output, runner = run_staged(review_case, [AIResponse(content, True), *[answer(stage) for stage in STAGES[1:]]])
    assert output.stages[0].parse_error
    assert output.stages[0].raw_response == content
    assert output.stages[0].assessment is None
    assert not output.completed
    assert runner.run.call_count == 5


@pytest.mark.parametrize('reference', ['stages.4.assessment', 'stages.0.assessment.findings.99', 'input.specification.content'])
def test_integration_rejects_untraceable_finding(review_case, reference):
    answers = [answer(stage) for stage in STAGES[:4]]
    answers.append(answer(STAGES[4], [finding('Evidence', 'Conflict', [reference])]))
    output, _ = run_staged(review_case, answers)
    assert output.integration.parse_error
    assert output.integration.assessment is None
    assert all(stage.assessment is not None for stage in output.stages)
    assert not output.completed


def test_mode_is_not_selected_from_input_size(review_case):
    from test_review_implementation import response
    c = review_case
    source = c['request'].repository_path / 'source.py'
    source.write_text('value = 1\n' * 10000, encoding='utf-8')
    output, runner = run_staged(c, [AIResponse(json.dumps(response()), True)], mode='BATCH')
    assert output.batch is not None
    assert output.stages == ()
    runner.run.assert_called_once()


def test_staged_execution_never_writes_or_reloads_artifacts(review_case):
    from application.semantic_staged_review import SemanticStagedReviewUseCase
    c = review_case
    prepared = c['use_case'].execute(c['request'])
    before = {p: p.read_bytes() for p in c['request'].repository_path.iterdir() if p.is_file()}
    runner = Mock()
    runner.run.side_effect = [answer(stage) for stage in STAGES]
    for dependency in ('repository', 'repository_state', 'test_provider', 'approvals'):
        c[dependency].reset_mock()
    output = SemanticStagedReviewUseCase(AIService(runner)).execute(prepared, mode='STAGED')
    for dependency in ('repository', 'repository_state', 'test_provider', 'approvals'):
        assert not c[dependency].mock_calls
    assert before == {p: p.read_bytes() for p in before}
    assert set(before) == {p for p in c['request'].repository_path.iterdir() if p.is_file()}
    assert output.prepared is prepared
