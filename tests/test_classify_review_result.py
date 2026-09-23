import json
from dataclasses import replace
from unittest.mock import Mock

import pytest
from core.ai.ai_response import AIResponse
from core.ai.ai_service import AIService
from application.review_findings import ReviewFinding, AspectReview, ReviewImplementationOutput, ASPECTS
from application.review_stages import StagedReviewOutput
from test_prepare_review_input import review_case


@pytest.fixture
def result_case(review_case):
    c = review_case
    prepared = c['use_case'].execute(c['request'])
    finding = ReviewFinding('Requirement', 'Required processing is absent', 'Specification requires validation', ('review_input.specification.content',), 'semantic')
    aspects = tuple(AspectReview(a, 'Compared approved requirements', (finding,) if a == 'Requirement' else (), ()) for a in ASPECTS)
    batch = ReviewImplementationOutput(prepared, aspects)
    return c, StagedReviewOutput('BATCH', prepared, batch=batch)


def evaluation(result='REVISION_REQUIRED'):
    return dict(result=result, rationale='Required validation is missing but correction is within approved scope',
                references=['review.batch.aspects.0.findings.0', 'review.prepared.review_input.implementation_plan.content'],
                checks={}, resolutions=[], problem='Missing required validation', cause='Implementation omitted validation',
                targets=['source.py'], safe_scope_reason='The approved plan explicitly requires validation in source.py',
                human_questions=[], unresolved=[])


def test_returns_revision_required_for_grounded_in_scope_correction_without_starting_correction(result_case):
    from application.classify_review_result import ClassifyReviewResultUseCase
    c, reviewed = result_case
    runner = Mock()
    runner.run.return_value = AIResponse(json.dumps(evaluation()), True)
    before = {p: p.read_bytes() for p in c['request'].repository_path.iterdir() if p.is_file()}
    output = ClassifyReviewResultUseCase(AIService(runner)).execute(reviewed)
    assert output.result.value == 'REVISION_REQUIRED'
    assert output.report.rationale == evaluation()['rationale']
    assert output.report.references[0] == 'review.batch.aspects.0.findings.0'
    assert output.review is reviewed
    assert output.review.prepared.mismatches == reviewed.prepared.mismatches
    assert output.report.targets == ('source.py',)
    assert output.report.safe_scope_reason
    assert before == {p: p.read_bytes() for p in before}
    assert runner.run.call_count == 1


def evaluate(review, payload=None, response=None):
    from application.classify_review_result import ClassifyReviewResultUseCase
    runner = Mock()
    runner.run.return_value = response or AIResponse(json.dumps(payload or evaluation()), True)
    return ClassifyReviewResultUseCase(AIService(runner)).execute(review), runner


def approved(review):
    data = evaluation('APPROVED')
    data.update(problem='', cause='', targets=[], safe_scope_reason='')
    data['checks'] = {key: dict(confirmed=True, rationale='Confirmed from artifacts', references=['review.prepared.review_input.specification.content'])
                      for key in ('specification', 'plan', 'scope', 'no_major_issues', 'tests_executed', 'test_behavior')}
    from application.review_result_prompt import result_context
    data['resolutions'] = [resolution(ref) for ref in result_context(review)['concerns']]
    return data


def resolution(ref):
    return dict(reference=ref, disagreement='The recorded concern', explanation='This does not imply nonconformance because the approved requirement is satisfied',
                references=['review.prepared.review_input.specification.content', ref])


def staged(review):
    from application.review_stages import STAGES, StageExecution, StageAssessment
    stages = tuple(StageExecution(stage, {}, StageAssessment('Checked', review.batch.aspects[i].findings, review.batch.aspects[i].unconfirmed)) for i, stage in enumerate(STAGES[:4]))
    integration = StageExecution(STAGES[4], {}, StageAssessment('Integrated', (), ()))
    return StagedReviewOutput('STAGED', review.prepared, stages, integration)


def proposal_for(review, result='REVISION_REQUIRED'):
    payload = evaluation(result)
    if review.mode == 'STAGED':
        payload['references'][0] = 'review.stages.0.assessment.findings.0'
    return payload


@pytest.mark.parametrize('mode', ['BATCH', 'STAGED'])
def test_grounded_approval_and_human_result_share_mode_contract(result_case, mode):
    _, review = result_case
    if mode == 'STAGED':
        review = staged(review)
    payload = approved(review)
    if mode == 'STAGED':
        payload['references'][0] = 'review.stages.0.assessment.findings.0'
    output, _ = evaluate(review, payload)
    assert output.result.value == 'APPROVED'
    assert output.review is review
    human = proposal_for(review, 'HUMAN_REVIEW_REQUIRED')
    human['human_questions'] = ['Specification is contradictory: which behavior is required?']
    output, _ = evaluate(review, human)
    assert output.result.value == 'HUMAN_REVIEW_REQUIRED'
    assert output.report.human_questions == tuple(human['human_questions'])


@pytest.mark.parametrize('key', ['specification', 'plan', 'scope', 'no_major_issues', 'tests_executed', 'test_behavior'])
def test_approval_requires_each_grounded_condition(result_case, key):
    _, review = result_case
    payload = approved(review)
    payload['checks'][key]['confirmed'] = False
    output, _ = evaluate(review, payload)
    assert output.result is None
    assert output.validation_errors
    assert output.report is not None


@pytest.mark.parametrize('field', ['problem', 'cause', 'targets', 'safe_scope_reason'])
def test_revision_requires_problem_cause_targets_and_scope_reason(result_case, field):
    _, review = result_case
    payload = evaluation()
    payload[field] = [] if field == 'targets' else ''
    output, _ = evaluate(review, payload)
    assert output.result is None
    assert output.validation_errors


def test_human_result_requires_human_question(result_case):
    output, _ = evaluate(result_case[1], evaluation('HUMAN_REVIEW_REQUIRED'))
    assert output.result is None
    assert output.validation_errors


def test_finding_zero_and_test_pass_do_not_supply_approval_reasons(result_case):
    _, review = result_case
    batch = replace(review.batch, aspects=tuple(replace(a, findings=()) for a in review.batch.aspects))
    review = replace(review, batch=batch)
    payload = evaluation('APPROVED')
    payload['references'] = ['review.prepared.review_input.test_state.full_test_result']
    output, _ = evaluate(review, payload)
    assert output.result is None
    assert output.validation_errors


def test_fail_alone_does_not_supply_revision_basis(result_case):
    _, review = result_case
    payload = evaluation()
    payload.update(problem='', cause='', targets=[], safe_scope_reason='')
    output, _ = evaluate(review, payload)
    assert output.result is None


@pytest.mark.parametrize('mode', ['BATCH', 'STAGED'])
def test_unresolved_and_resolved_mechanical_mismatch_preserve_original(result_case, mode):
    from application.review_input import ReviewMismatch
    _, review = result_case
    prepared = replace(review.prepared, mismatches=(ReviewMismatch('test.full_test_result', 'PASS', 'FAIL'),))
    review = replace(review, prepared=prepared, batch=replace(review.batch, prepared=prepared))
    if mode == 'STAGED':
        review = staged(review)
    payload = approved(review)
    payload['references'] = ['review.prepared.review_input.specification.content']
    payload['resolutions'] = [r for r in payload['resolutions'] if r['reference'] != 'review.prepared.mismatches.0']
    output, _ = evaluate(review, payload)
    assert output.result is None
    assert output.validation_errors
    payload['resolutions'].append(resolution('review.prepared.mismatches.0'))
    output, _ = evaluate(review, payload)
    assert output.result.value == 'APPROVED'
    assert output.review.prepared.mismatches is prepared.mismatches
    assert output.report.resolutions


def test_integration_conflict_requires_resolution_and_is_never_erased(result_case):
    review = staged(result_case[1])
    conflict = ReviewFinding('Implementation', 'Conflicting stage findings', 'Stage evidence differs', ('stages.0.assessment.findings.0',), 'semantic')
    review = replace(review, integration=replace(review.integration, assessment=replace(review.integration.assessment, findings=(conflict,))))
    payload = approved(review)
    payload['references'] = ['review.integration.assessment.findings.0']
    ref = 'review.integration.assessment.findings.0'
    payload['resolutions'] = [r for r in payload['resolutions'] if r['reference'] != ref]
    output, _ = evaluate(review, payload)
    assert output.result is None
    payload['resolutions'].append(resolution(ref))
    output, _ = evaluate(review, payload)
    assert output.result.value == 'APPROVED'
    assert output.review.integration.assessment.findings == (conflict,)


@pytest.mark.parametrize('result', ['APPROVED', 'REVISION_REQUIRED', 'HUMAN_REVIEW_REQUIRED'])
@pytest.mark.parametrize('failure', ['execution', 'parse', 'missing_stage', 'missing_input'])
def test_required_review_failure_blocks_all_results_and_keeps_human_issue(result_case, result, failure):
    review = staged(result_case[1])
    first = replace(review.stages[0], assessment=replace(review.stages[0].assessment, unconfirmed=('Specification is contradictory; Human must decide',)))
    stages = (first, *review.stages[1:])
    if failure == 'execution':
        stages = (*stages[:3], replace(stages[3], assessment=None, execution_error='AI unavailable'))
    elif failure == 'parse':
        stages = (*stages[:3], replace(stages[3], assessment=None, parse_error='Invalid response'))
    elif failure == 'missing_stage':
        stages = stages[:3]
    review = replace(review, stages=stages)
    if failure == 'missing_input':
        review = replace(review, prepared=replace(review.prepared, review_input=None, missing_information=('specification',)))
    output, runner = evaluate(review, proposal_for(review, result))
    assert output.result is None
    assert output.review_failures
    assert output.review.stages[0].assessment.unconfirmed
    runner.run.assert_not_called()


def test_semantic_uncertainty_is_not_technical_review_failure(result_case):
    _, review = result_case
    aspects = (replace(review.batch.aspects[0], unconfirmed=('Specification is ambiguous',)), *review.batch.aspects[1:])
    review = replace(review, batch=replace(review.batch, aspects=aspects))
    assert not review.completed
    payload = evaluation('HUMAN_REVIEW_REQUIRED')
    payload['human_questions'] = ['Which specification behavior is intended?']
    output, runner = evaluate(review, payload)
    assert output.result.value == 'HUMAN_REVIEW_REQUIRED'
    assert not output.review_failures
    runner.run.assert_called_once()


@pytest.mark.parametrize('kind', ['exception', 'reported', 'parse'])
def test_result_evaluation_failure_is_not_a_result(result_case, kind):
    from application.classify_review_result import ClassifyReviewResultUseCase
    review = result_case[1]
    runner = Mock()
    if kind == 'exception':
        runner.run.side_effect = RuntimeError('AI unavailable')
    elif kind == 'reported':
        runner.run.return_value = AIResponse('', False, 'AI unavailable')
    else:
        runner.run.return_value = AIResponse('invalid JSON', True)
    output = ClassifyReviewResultUseCase(AIService(runner)).execute(review)
    assert output.result is None
    assert output.review is review
    assert output.report is None
    if kind == 'parse':
        assert output.parse_error and output.execution_error is None
    else:
        assert output.execution_error and output.parse_error is None
    runner.run.assert_called_once()


@pytest.mark.parametrize('error', ['execution_error', 'parse_error'])
def test_batch_failure_blocks_classification_without_erasing_findings(result_case, error):
    _, review = result_case
    review = replace(review, batch=replace(review.batch, **{error: 'Review failed'}))
    output, runner = evaluate(review)
    assert output.result is None
    assert output.review_failures
    assert output.review.batch.aspects[0].findings
    runner.run.assert_not_called()


@pytest.mark.parametrize('where', range(5))
def test_any_required_staged_failure_prevents_result(result_case, where):
    review = staged(result_case[1])
    if where == 4:
        review = replace(review, integration=replace(review.integration, parse_error='Invalid integration'))
    else:
        stages = list(review.stages)
        stages[where] = replace(stages[where], execution_error='AI failed')
        review = replace(review, stages=tuple(stages))
    output, runner = evaluate(review)
    assert output.result is None
    assert output.review_failures
    runner.run.assert_not_called()


@pytest.mark.parametrize('count', [1, 4, 20])
def test_finding_count_does_not_determine_result(result_case, count):
    _, review = result_case
    first = replace(review.batch.aspects[0], findings=review.batch.aspects[0].findings * count)
    review = replace(review, batch=replace(review.batch, aspects=(first, *review.batch.aspects[1:])))
    for expected in ('REVISION_REQUIRED', 'HUMAN_REVIEW_REQUIRED'):
        payload = evaluation(expected)
        if expected == 'HUMAN_REVIEW_REQUIRED':
            payload['human_questions'] = ['Required correction may exceed approved scope; Human must decide']
        output, _ = evaluate(review, payload)
        assert output.result.value == expected
        assert len(output.review.batch.aspects[0].findings) == count


@pytest.mark.parametrize('problem', ['fourth_result', 'unknown_reference', 'no_reference', 'blank_reason', 'extra_field', 'bad_check', 'empty_check_reason', 'empty_resolution_reason', 'unrelated_resolution', 'self_only_resolution', 'wrong_type'])
def test_invalid_semantic_report_is_not_normalized_into_result(result_case, problem):
    _, review = result_case
    payload = approved(review)
    if problem == 'fourth_result':
        payload['result'] = 'FAILED'
    elif problem == 'unknown_reference':
        payload['references'] = ['review.unknown']
    elif problem == 'no_reference':
        payload['references'] = []
    elif problem == 'blank_reason':
        payload['rationale'] = ''
    elif problem == 'extra_field':
        payload['severity'] = 'high'
    elif problem == 'bad_check':
        payload['checks']['scope']['confirmed'] = 'true'
    elif problem == 'empty_check_reason':
        payload['checks']['scope']['rationale'] = ''
    elif problem == 'empty_resolution_reason':
        payload['resolutions'][0]['explanation'] = ''
    elif problem == 'unrelated_resolution':
        payload['resolutions'][0]['reference'] = 'review.prepared.review_input.specification.content'
    elif problem == 'self_only_resolution':
        payload['resolutions'][0]['references'] = [payload['resolutions'][0]['reference']]
    else:
        payload['targets'] = 'source.py'
    output, _ = evaluate(review, payload)
    assert output.result is None
    assert output.parse_error or output.validation_errors
    assert output.raw_response == json.dumps(payload)


@pytest.mark.parametrize('status,result', [('COMPLETED', 'PASS'), ('COMPLETED', 'FAIL'), ('ERROR', 'NONE')])
def test_test_state_alone_never_selects_result(result_case, status, result):
    _, review = result_case
    input_data = review.prepared.review_input
    input_data = replace(input_data, test_state=replace(input_data.test_state, full_test_status=status, full_test_result=result))
    prepared = replace(review.prepared, review_input=input_data)
    review = replace(review, prepared=prepared, batch=replace(review.batch, prepared=prepared))
    payload = evaluation('REVISION_REQUIRED')
    payload.update(problem='', cause='', targets=[], safe_scope_reason='')
    output, runner = evaluate(review, payload)
    assert output.result is None
    assert output.validation_errors
    assert output.review.prepared.review_input.test_state.full_test_result == result
    prompt_data = json.loads(runner.run.call_args.args[0].prompt.split('# Result Input\n', 1)[1])
    assert prompt_data['review']['prepared']['review_input']['test_state']['full_test_status'] == status


def test_approved_cannot_leave_unresolved_or_human_questions(result_case):
    _, review = result_case
    for field in ('unresolved', 'human_questions'):
        payload = approved(review)
        payload[field] = ['Scope is not confirmed']
        output, _ = evaluate(review, payload)
        assert output.result is None
        assert output.report is not None
        assert output.validation_errors


def test_revision_does_not_hide_required_human_decision(result_case):
    payload = evaluation()
    payload['human_questions'] = ['Plan modification requires Human judgment']
    output, _ = evaluate(result_case[1], payload)
    assert output.result is None
    assert output.report.human_questions


def test_result_evaluation_does_not_reload_or_mutate_artifacts(result_case):
    c, review = result_case
    for dependency in ('repository', 'repository_state', 'test_provider', 'approvals'):
        c[dependency].reset_mock()
    root = c['request'].repository_path
    before = {p: p.read_bytes() for p in root.iterdir() if p.is_file()}
    output, _ = evaluate(review)
    assert output.result.value == 'REVISION_REQUIRED'
    assert before == {p: p.read_bytes() for p in root.iterdir() if p.is_file()}
    for dependency in ('repository', 'repository_state', 'test_provider', 'approvals'):
        assert not c[dependency].mock_calls


def test_prompt_exposes_common_conditions_and_keeps_evidence_sources(result_case):
    from application.review_result_prompt import result_context, build_result_prompt
    _, review = result_case
    review = staged(review)
    prompt = build_result_prompt(result_context(review))
    assert prompt.is_ready
    for field in ('specification', 'plan', 'scope', 'no_major_issues', 'tests_executed', 'test_behavior', 'resolutions', 'safe_scope_reason', 'human_questions'):
        assert field in prompt.content
    context = json.loads(prompt.content.split('# Result Input\n', 1)[1])
    assert context['review']['prepared']['review_input']['evidence']['identity']['base_branch'] == 'release/base'
    assert context['review']['prepared']['review_input']['test_state']['initial_test_result'] == 'FAIL'
    assert len(context['review']['stages']) == 4
    assert context['review']['integration']['assessment']
    assert context['concerns'] == ['review.stages.0.assessment.findings.0']


def test_unresolved_diagnosis_does_not_automatically_choose_revision_or_human(result_case):
    from application.review_input import ReviewMismatch
    _, review = result_case
    prepared = replace(review.prepared, mismatches=(ReviewMismatch('repository.branch', 'impl/a', 'impl/b'),))
    review = replace(review, prepared=prepared, batch=replace(review.batch, prepared=prepared))
    for expected in ('REVISION_REQUIRED', 'HUMAN_REVIEW_REQUIRED'):
        payload = evaluation(expected)
        if expected == 'HUMAN_REVIEW_REQUIRED':
            payload['human_questions'] = ['Cannot safely establish required correction scope; Human must identify target']
        output, _ = evaluate(review, payload)
        assert output.result.value == expected
        assert output.review.prepared.mismatches


def test_collection_diagnostics_cannot_be_silently_dropped_from_approval(result_case):
    _, review = result_case
    acquired = replace(review.prepared.acquired, request=replace(review.prepared.acquired.request, collection_inconsistencies=('Phase 4 inconsistency',), collection_human_approval_required=('Scope confirmation',)))
    prepared = replace(review.prepared, acquired=acquired)
    review = replace(review, prepared=prepared, batch=replace(review.batch, prepared=prepared))
    payload = approved(review)
    payload['resolutions'] = [r for r in payload['resolutions'] if not r['reference'].startswith('review.prepared.acquired')]
    output, _ = evaluate(review, payload)
    assert output.result is None
    assert output.review.prepared.acquired.request.collection_human_approval_required == ('Scope confirmation',)
    assert any('collection_inconsistencies' in error for error in output.validation_errors)


@pytest.mark.parametrize('content', ['null', '[]', '{"result": "APPROVED", "result": "REVISION_REQUIRED"}'])
def test_non_object_or_duplicate_response_is_parse_failure(result_case, content):
    output, _ = evaluate(result_case[1], response=AIResponse(content, True))
    assert output.result is None
    assert output.parse_error
    assert output.raw_response == content
