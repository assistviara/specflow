from dataclasses import replace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from core.ai.ai_request import AIRequest
from core.ai.ai_response import AIResponse
from core.ai.ai_service import AIService
from test_classify_review_result import result_case
from test_prepare_review_input import review_case


def permit(operation, failure):
    from application.review_retry import RetryAuthorization
    return RetryAuthorization(
        temporary_ai_failure=True, same_request_safe=True,
        artifacts_unchanged=True, conditions_unchanged=True,
        changes_required=False, reason='Transient service outage; read-only request and conditions verified',
    )


def test_retries_safe_review_operation_with_same_input_preserving_failure_and_findings(result_case):
    from application.review_retry import ReviewAIOperation, ReviewOperationKind
    from application.technical_review_retry import TechnicalReviewRetryUseCase
    c, review = result_case
    review = replace(review, batch=replace(review.batch, aspects=(replace(review.batch.aspects[0], unconfirmed=('Human must clarify requirement',)), *review.batch.aspects[1:])))
    request = AIRequest('Unchanged review request')
    operation = ReviewAIOperation(uuid4(), ReviewOperationKind.BATCH, request, review)
    original = AIResponse('original failure detail', False, 'Temporary service failure')
    recovered = AIResponse('Recovered review response', True)
    runner = Mock()
    runner.run.side_effect = [original, recovered]
    before = {p: p.read_bytes() for p in c['request'].repository_path.iterdir() if p.is_file()}

    history = TechnicalReviewRetryUseCase(AIService(runner), permit).execute(operation)

    assert runner.run.call_count == 2
    assert all(call.args[0] is request for call in runner.run.call_args_list)
    assert history.retry_count == 1
    assert history.recovered
    assert not history.recovery_failed
    assert history.original.response is original
    assert history.retry.response is recovered
    assert history.authorization.reason
    assert history.operation.context is review
    assert history.operation.context.batch.aspects[0].findings
    assert history.operation.context.batch.aspects[0].unconfirmed
    assert not hasattr(history, 'result')
    assert before == {p: p.read_bytes() for p in before}


def operation(review, kind=None):
    from application.review_retry import ReviewAIOperation, ReviewOperationKind
    return ReviewAIOperation(uuid4(), kind or ReviewOperationKind.BATCH, AIRequest('Same prompt and embedded input'), review)


@pytest.mark.parametrize('field,value', [
    ('temporary_ai_failure', False), ('same_request_safe', False),
    ('artifacts_unchanged', False), ('conditions_unchanged', False),
    ('changes_required', True), ('reason', ''), ('same_request_safe', None),
    ('temporary_ai_failure', 'true'),
])
def test_retry_requires_explicit_safety_and_no_changes(result_case, field, value):
    from application.technical_review_retry import TechnicalReviewRetryUseCase
    op = operation(result_case[1])
    runner = Mock()
    runner.run.return_value = AIResponse('', False, 'Error')
    authorization = replace(permit(op, None), **{field: value})
    history = TechnicalReviewRetryUseCase(AIService(runner), lambda *_: authorization).execute(op)
    assert history.retry_count == 0
    assert not history.recovery_failed
    assert history.original.response.error_message == 'Error'
    runner.run.assert_called_once_with(op.request)


def test_retry_is_once_per_identified_operation_even_if_submitted_again(result_case):
    from application.technical_review_retry import TechnicalReviewRetryUseCase
    op = operation(result_case[1])
    runner = Mock()
    original = AIResponse('first', False, 'temporary failure')
    retried = AIResponse('second', False, 'still unavailable')
    runner.run.side_effect = [original, retried]
    use_case = TechnicalReviewRetryUseCase(AIService(runner), permit)
    first = use_case.execute(op)
    second = use_case.execute(op)
    assert first is second
    assert first.recovery_failed
    assert first.retry_count == 1
    assert first.original.response is original
    assert first.retry.response is retried
    assert runner.run.call_count == 2


def test_operation_identity_cannot_be_reused_with_changed_request(result_case):
    from application.technical_review_retry import TechnicalReviewRetryUseCase
    op = operation(result_case[1])
    runner = Mock()
    runner.run.return_value = AIResponse('done', True)
    use_case = TechnicalReviewRetryUseCase(AIService(runner), permit)
    use_case.execute(op)
    with pytest.raises(ValueError):
        use_case.execute(replace(op, request=AIRequest('changed prompt')))
    runner.run.assert_called_once()


@pytest.mark.parametrize('kind', ['Test FAIL', 'Test Execution', 'Parse', 'Input acquisition', 'Finding', 'Human Review'])
def test_only_seven_review_ai_operations_are_accepted(result_case, kind):
    from application.technical_review_retry import TechnicalReviewRetryUseCase
    runner = Mock()
    with pytest.raises(ValueError):
        TechnicalReviewRetryUseCase(AIService(runner), permit).execute(operation(result_case[1], kind))
    runner.run.assert_not_called()


@pytest.mark.parametrize('response_text', ['FAIL', 'ERROR', 'invalid JSON', 'Human decision required', 'mechanical mismatch'])
def test_successful_ai_response_is_not_retried_based_on_text(result_case, response_text):
    from application.technical_review_retry import TechnicalReviewRetryUseCase
    runner = Mock()
    runner.run.return_value = AIResponse(response_text, True)
    authorize = Mock()
    history = TechnicalReviewRetryUseCase(AIService(runner), authorize).execute(operation(result_case[1]))
    assert history.retry_count == 0
    runner.run.assert_called_once()
    authorize.assert_not_called()


def test_safety_assessment_failure_keeps_original_failure_without_retry(result_case):
    from application.technical_review_retry import TechnicalReviewRetryUseCase
    runner = Mock()
    runner.run.return_value = AIResponse('original', False, 'temporary')
    authorize = Mock(side_effect=ValueError('Safety unknown'))
    history = TechnicalReviewRetryUseCase(AIService(runner), authorize).execute(operation(result_case[1]))
    assert history.retry_count == 0
    assert history.original.response.content == 'original'
    assert history.decision_error
    runner.run.assert_called_once()

from test_semantic_staged_review import answer, finding, context, STAGES
from test_review_implementation import response as batch_response
from test_classify_review_result import evaluation


def test_staged_retries_only_failed_operation_then_continues_fixed_order(review_case):
    from application.review_with_retry import ReviewWithRetryUseCase
    c = review_case
    c['test_provider'].get_state.return_value = replace(c['actual'], full_test_result='FAIL')
    prepared = c['use_case'].execute(c['request'])
    first = answer(STAGES[0], [finding('Requirement', 'Known requirement issue', ['input.specification.content'])], ['Human must clarify requirement'])
    runner = Mock()
    runner.run.side_effect = [first, answer(STAGES[1]), AIResponse('original', False, 'Transient connection failure'), answer(STAGES[2]), answer(STAGES[3]), answer(STAGES[4])]
    output = ReviewWithRetryUseCase(AIService(runner), permit).execute(prepared, mode='STAGED')
    requests = [call.args[0] for call in runner.run.call_args_list]
    assert [context(request)['stage'] for request in requests] == [*STAGES[:3], *STAGES[2:]]
    assert requests[2] is requests[3]
    assert output.history[2].recovered
    assert output.history[2].retry_count == 1
    assert output.history[2].original.response.content == 'original'
    assert output.review.stages[0].assessment.findings
    assert output.review.stages[0].assessment.unconfirmed
    assert output.review.prepared.mismatches
    assert output.review.integration is not None
    assert output.classification is None
    assert not output.recovery_failed


def test_recovery_failed_stops_before_later_stages_and_preserves_partial_review(review_case):
    from application.review_with_retry import ReviewWithRetryUseCase
    prepared = review_case['use_case'].execute(review_case['request'])
    runner = Mock()
    runner.run.side_effect = [answer(STAGES[0], [finding('Requirement', 'Known issue', ['input.specification.content'])], ['Human judgment needed']), answer(STAGES[1]), AIResponse('original', False, 'Transient'), AIResponse('retry', False, 'Still unavailable')]
    use_case = ReviewWithRetryUseCase(AIService(runner), permit)
    output = use_case.execute(prepared, mode='STAGED')
    assert runner.run.call_count == 4
    assert output.recovery_failed
    assert len(output.review.stages) == 3
    assert output.review.integration is None
    assert output.review.stages[0].assessment.findings
    assert output.review.stages[0].assessment.unconfirmed
    assert output.history[-1].original.response.content == 'original'
    assert output.history[-1].retry.response.content == 'retry'
    classified = use_case.classify(output)
    assert classified.classification.result is None
    assert classified.classification.review_failures
    assert classified.history == output.history
    assert runner.run.call_count == 4


def test_integration_failure_retries_only_integration(review_case):
    from application.review_with_retry import ReviewWithRetryUseCase
    runner = Mock()
    runner.run.side_effect = [*[answer(stage) for stage in STAGES[:4]], AIResponse('', False, 'Transient'), answer(STAGES[4])]
    output = ReviewWithRetryUseCase(AIService(runner), permit).execute(review_case['use_case'].execute(review_case['request']), mode='STAGED')
    assert [context(call.args[0])['stage'] for call in runner.run.call_args_list] == [*STAGES, STAGES[4]]
    assert output.history[-1].recovered
    assert output.review.integration.completed


def test_batch_ai_failure_retries_without_generating_result(review_case):
    from application.review_with_retry import ReviewWithRetryUseCase
    import json
    runner = Mock()
    runner.run.side_effect = [AIResponse('', False, 'Transient'), AIResponse(json.dumps(batch_response()), True)]
    output = ReviewWithRetryUseCase(AIService(runner), permit).execute(review_case['use_case'].execute(review_case['request']), mode='BATCH')
    assert runner.run.call_count == 2
    assert runner.run.call_args_list[0].args[0] is runner.run.call_args_list[1].args[0]
    assert output.review.batch.completed
    assert output.classification is None
    assert output.history[0].recovered


def test_target_four_ai_failure_retries_through_existing_classification(result_case):
    from application.review_with_retry import ReviewWithRetryUseCase
    import json
    _, review = result_case
    runner = Mock()
    runner.run.side_effect = [AIResponse('original', False, 'Transient'), AIResponse(json.dumps(evaluation()), True)]
    output = ReviewWithRetryUseCase(AIService(runner), permit).classify(review)
    assert output.classification.result.value == 'REVISION_REQUIRED'
    assert output.classification.review is review
    assert output.history[0].operation.kind.value == 'Review Result Classification'
    assert output.history[0].recovered
    assert runner.run.call_count == 2
    assert runner.run.call_args_list[0].args[0] is runner.run.call_args_list[1].args[0]


@pytest.mark.parametrize('status,result', [('COMPLETED', 'PASS'), ('COMPLETED', 'FAIL'), ('ERROR', 'NONE')])
def test_test_states_do_not_trigger_retry_or_test_runner(review_case, status, result):
    from application.review_with_retry import ReviewWithRetryUseCase
    import json
    c = review_case
    c['test_provider'].get_state.return_value = replace(c['actual'], full_test_status=status, full_test_result=result, errors=('Recorded test error',) if status == 'ERROR' else ())
    prepared = c['use_case'].execute(c['request'])
    runner = Mock()
    runner.run.return_value = AIResponse(json.dumps(batch_response()), True)
    authorize = Mock()
    output = ReviewWithRetryUseCase(AIService(runner), authorize).execute(prepared, mode='BATCH')
    assert output.history[0].retry_count == 0
    assert output.review.prepared.review_input.test_state.full_test_result == result
    assert output.classification is None
    runner.run.assert_called_once()
    authorize.assert_not_called()


def test_target_one_acquisition_failure_is_not_retried(review_case):
    from application.review_with_retry import ReviewWithRetryUseCase
    c = review_case
    c['evidence'].basis.specification_path.unlink()
    prepared = c['use_case'].execute(c['request'])
    runner, authorize = Mock(), Mock()
    output = ReviewWithRetryUseCase(AIService(runner), authorize).execute(prepared, mode='STAGED')
    assert output.review.prepared.missing_information
    assert output.history == ()
    assert not output.review.completed
    runner.run.assert_not_called()
    authorize.assert_not_called()


@pytest.mark.parametrize('kind', ['BATCH', 'STAGED', 'CLASSIFICATION'])
def test_parse_failure_is_never_retried(result_case, kind):
    from application.review_with_retry import ReviewWithRetryUseCase
    _, review = result_case
    runner, authorize = Mock(), Mock()
    runner.run.return_value = AIResponse('invalid JSON', True)
    use_case = ReviewWithRetryUseCase(AIService(runner), authorize)
    if kind == 'CLASSIFICATION':
        output = use_case.classify(review)
        assert output.classification.parse_error
        assert output.classification.result is None
    else:
        output = use_case.execute(review.prepared, mode=kind)
        if kind == 'BATCH':
            assert output.review.batch.parse_error
        else:
            assert all(stage.parse_error for stage in output.review.stages)
    assert runner.run.call_count == (5 if kind == 'STAGED' else 1)
    assert all(item.retry_count == 0 for item in output.history)
    authorize.assert_not_called()


def test_semantic_findings_uncertainty_and_mismatch_never_authorize_retry(review_case):
    from application.review_with_retry import ReviewWithRetryUseCase
    from application.review_input import ReviewMismatch
    import json
    c = review_case
    prepared = c['use_case'].execute(c['request'])
    prepared = replace(prepared, mismatches=(ReviewMismatch('repository.branch', 'a', 'b'),))
    payload = batch_response()
    payload['aspects'][0]['findings'] = [dict(description='Specification is contradictory', rationale='Conflicting requirements', references=['review_input.specification.content'])]
    payload['aspects'][0]['unconfirmed'] = ['Human judgment required']
    runner, authorize = Mock(), Mock()
    runner.run.return_value = AIResponse(json.dumps(payload), True)
    output = ReviewWithRetryUseCase(AIService(runner), authorize).execute(prepared, mode='BATCH')
    assert output.review.batch.aspects[0].findings
    assert output.review.batch.aspects[0].unconfirmed
    assert output.review.prepared.mismatches
    assert not output.review.completed
    assert output.history[0].retry_count == 0
    runner.run.assert_called_once()
    authorize.assert_not_called()


def test_validation_failure_is_not_retried(result_case):
    from application.review_with_retry import ReviewWithRetryUseCase
    import json
    payload = evaluation('APPROVED')
    runner, authorize = Mock(), Mock()
    runner.run.return_value = AIResponse(json.dumps(payload), True)
    output = ReviewWithRetryUseCase(AIService(runner), authorize).classify(result_case[1])
    assert output.classification.result is None
    assert output.classification.validation_errors
    assert output.history[0].retry_count == 0
    authorize.assert_not_called()
    runner.run.assert_called_once()


@pytest.mark.parametrize('position', range(5))
def test_recovery_failed_stops_at_each_stage_without_second_retry(review_case, position):
    from application.review_with_retry import ReviewWithRetryUseCase
    runner = Mock()
    runner.run.side_effect = [*[answer(stage) for stage in STAGES[:position]], RuntimeError('transient original'), RuntimeError('retry failed')]
    output = ReviewWithRetryUseCase(AIService(runner), permit).execute(review_case['use_case'].execute(review_case['request']), mode='STAGED')
    assert runner.run.call_count == position + 2
    assert output.recovery_failed
    assert output.history[-1].original.execution_error == 'RuntimeError: transient original'
    assert output.history[-1].retry.execution_error == 'RuntimeError: retry failed'
    assert output.history[-1].retry_count == 1
    if position < 4:
        assert len(output.review.stages) == position + 1
        assert output.review.integration is None
    else:
        assert output.review.integration.execution_error


def test_retry_success_with_unparseable_response_is_not_review_recovery(result_case):
    from application.review_with_retry import ReviewWithRetryUseCase
    runner = Mock()
    runner.run.side_effect = [AIResponse('', False, 'Transient'), AIResponse('invalid JSON', True)]
    use_case = ReviewWithRetryUseCase(AIService(runner), permit)
    output = use_case.execute(result_case[1].prepared, mode='BATCH')
    assert output.history[0].recovered  # AI execution recovered; parsing did not.
    assert output.review.batch.parse_error
    classified = use_case.classify(output)
    assert classified.classification.result is None
    assert classified.classification.review_failures
    assert runner.run.call_count == 2


def test_failed_classification_outcome_cannot_be_retried_again(result_case):
    from application.review_with_retry import ReviewWithRetryUseCase
    runner = Mock()
    runner.run.return_value = AIResponse('', False, 'Still unavailable')
    use_case = ReviewWithRetryUseCase(AIService(runner), permit)
    first = use_case.classify(result_case[1])
    second = use_case.classify(first)
    assert first is second
    assert second.recovery_failed
    assert second.classification.result is None
    assert runner.run.call_count == 2


def test_no_retry_without_safety_confirmation_in_batch_or_classifier(result_case):
    from application.review_retry import RetryAuthorization
    from application.review_with_retry import ReviewWithRetryUseCase
    runner = Mock()
    runner.run.return_value = AIResponse('', False, 'Error')
    use_case = ReviewWithRetryUseCase(AIService(runner), lambda *_: RetryAuthorization())
    batch = use_case.execute(result_case[1].prepared, mode='BATCH')
    classified = use_case.classify(result_case[1])
    assert batch.history[0].retry_count == 0
    assert classified.history[0].retry_count == 0
    assert classified.classification.result is None
    assert runner.run.call_count == 2


def test_recovered_staged_review_connects_to_target_four_without_repeating_review(review_case):
    from application.review_with_retry import ReviewWithRetryUseCase
    import json
    prepared = review_case['use_case'].execute(review_case['request'])
    payload = evaluation('HUMAN_REVIEW_REQUIRED')
    payload['references'][0] = 'review.stages.0.assessment.findings.0'
    payload['human_questions'] = ['Specification ambiguity requires Human judgment']
    runner = Mock()
    runner.run.side_effect = [
        answer(STAGES[0], [finding('Requirement', 'Ambiguous requirement', ['input.specification.content'])], ['Human judgment required']),
        answer(STAGES[1]), AIResponse('', False, 'Transient'), answer(STAGES[2]), answer(STAGES[3]), answer(STAGES[4]),
        AIResponse(json.dumps(payload), True),
    ]
    use_case = ReviewWithRetryUseCase(AIService(runner), permit)
    reviewed = use_case.execute(prepared, mode='STAGED')
    assert reviewed.classification is None
    assert runner.run.call_count == 6
    classified = use_case.classify(reviewed)
    assert runner.run.call_count == 7
    assert classified.classification.result.value == 'HUMAN_REVIEW_REQUIRED'
    assert classified.classification.review is reviewed.review
    assert classified.history[:5] == reviewed.history
    assert classified.history[2].recovered
    assert classified.review.stages[0].assessment.unconfirmed


def test_review_with_retry_preserves_files_and_does_not_reacquire_input(review_case):
    from application.review_with_retry import ReviewWithRetryUseCase
    import json
    c = review_case
    prepared = c['use_case'].execute(c['request'])
    for dependency in ('repository', 'repository_state', 'test_provider', 'approvals'):
        c[dependency].reset_mock()
    root = c['request'].repository_path
    before = {p: p.read_bytes() for p in root.iterdir() if p.is_file()}
    runner = Mock()
    runner.run.side_effect = [AIResponse('', False, 'Transient'), AIResponse(json.dumps(batch_response()), True)]
    output = ReviewWithRetryUseCase(AIService(runner), permit).execute(prepared, mode='BATCH')
    assert output.review.prepared is prepared
    assert before == {p: p.read_bytes() for p in root.iterdir() if p.is_file()}
    for dependency in ('repository', 'repository_state', 'test_provider', 'approvals'):
        assert not c[dependency].mock_calls


@pytest.mark.parametrize('kind', ['REQUIREMENT', 'CHANGE_SCOPE', 'IMPLEMENTATION', 'TEST', 'INTEGRATION', 'BATCH', 'RESULT_CLASSIFICATION'])
def test_all_seven_operations_use_the_same_retry_safety_contract(result_case, kind):
    from application.review_retry import ReviewOperationKind
    from application.technical_review_retry import TechnicalReviewRetryUseCase
    runner = Mock()
    runner.run.side_effect = [RuntimeError('Temporary outage'), AIResponse('Recovered', True)]
    op = operation(result_case[1], ReviewOperationKind[kind])
    use_case = TechnicalReviewRetryUseCase(AIService(runner), permit)
    history = use_case.execute(op)
    assert history.retry_count == 1
    assert history.recovered
    assert history.original.execution_error == 'RuntimeError: Temporary outage'
    assert use_case.execute(op) is history
    assert runner.run.call_count == 2


def test_core_cannot_reenter_same_operation_during_safety_assessment(result_case):
    from application.technical_review_retry import TechnicalReviewRetryUseCase
    op = operation(result_case[1])
    runner = Mock()
    runner.run.side_effect = [AIResponse('', False, 'Temporary outage'), AIResponse('Recovered', True)]
    def authorize(operation, failure):
        with pytest.raises(ValueError):
            use_case.execute(operation)
        return permit(operation, failure)
    use_case = TechnicalReviewRetryUseCase(AIService(runner), authorize)
    history = use_case.execute(op)
    assert history.recovered
    assert runner.run.call_count == 2
