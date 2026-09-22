import json
from dataclasses import asdict, replace
from unittest.mock import Mock

import pytest

from application.review_result import ReviewResult, ReviewResultOutput, ReviewResultReport
from application.review_input import ReviewMismatch
from core.ai.ai_response import AIResponse
from core.ai.ai_service import AIService
from test_classify_review_result import result_case, evaluation
from test_prepare_review_input import review_case


BASE = 'review.prepared.review_input'
FINDING = 'review.batch.aspects.0.findings.0'


@pytest.fixture
def routing_case(result_case):
    from application.correction_routing import CorrectionProblem, RoutingControl, CorrectionRoutingInput

    c, reviewed = result_case
    prepared = replace(reviewed.prepared, mismatches=(ReviewMismatch('test.full_test_result', 'PASS', 'FAIL'),))
    reviewed = replace(reviewed, prepared=prepared)
    data = evaluation()
    data['proposed_result'] = ReviewResult(data.pop('result'))
    for key in ('references', 'resolutions', 'targets', 'human_questions', 'unresolved'):
        data[key] = tuple(data[key])
    result = ReviewResultOutput(reviewed, ReviewResult.REVISION_REQUIRED, ReviewResultReport(**data))
    problem = CorrectionProblem(
        destination='Codex再実装工程', targets=('source.py',), finding_references=(FINDING,),
        scope_reference=f'{BASE}.evidence.scope', safe_in_scope=True,
        safe_scope_reason=result.report.safe_scope_reason,
        required_test_references=(f'{BASE}.evidence.verification.test_commands',),
        correction_references=(f'{BASE}.implementation_plan.content',),
        safe_group='approved-validation',
    )
    request = CorrectionRoutingInput(result, (problem,), 'reviewing', RoutingControl(True, 0, False, True))
    runner = Mock()

    def respond(ai_request):
        # The AI structures an instruction using only the supplied grounded fields.
        context = json.loads(ai_request.prompt.split('CORRECTION_INPUT\n', 1)[1])
        return AIResponse(json.dumps({'instructions': context['instructions']}), True)

    runner.run.side_effect = respond
    return c, request, runner


def test_prepares_in_scope_correction_instruction_preserving_review_without_executing_correction(routing_case):
    from application.prepare_correction import PrepareCorrectionUseCase

    c, request, runner = routing_case
    before = {p: p.read_bytes() for p in c['request'].repository_path.iterdir() if p.is_file()}
    output = PrepareCorrectionUseCase(AIService(runner)).execute(request)

    assert output.ready
    assert len(output.instructions) == 1
    instruction = output.instructions[0]
    assert instruction.destination == 'Codex再実装工程'
    assert instruction.problem == request.review.report.problem
    assert instruction.cause == request.review.report.cause
    assert instruction.targets == ('source.py',)
    assert instruction.rationale == request.review.report.rationale
    assert instruction.review_reference == 'result'
    assert instruction.finding_references == (FINDING,)
    assert instruction.scope_reference == f'{BASE}.evidence.scope'
    assert instruction.allowed_changes == ('*.py',)
    assert instruction.forbidden_changes == ()
    assert instruction.safe_scope_reasons == (request.review.report.safe_scope_reason,)
    assert instruction.required_test_references
    assert instruction.correction_references
    assert instruction.basis_references
    assert output.request is request
    assert output.request.review.review.prepared.mismatches[0].actual == 'FAIL'
    assert output.request.review.review.batch.aspects[0].findings is request.review.review.batch.aspects[0].findings
    assert output.request.control.correction_count == 0
    assert before == {p: p.read_bytes() for p in before}
    runner.run.assert_called_once()
    c['repository'].save.assert_not_called()
    c['approvals'].save.assert_not_called()


@pytest.mark.parametrize('mode', ['BATCH', 'STAGED'])
def test_mode_contract_preserves_history_scope_and_never_executes_following_roles(routing_case, mode, monkeypatch):
    from application.prepare_correction import PrepareCorrectionUseCase
    from application.review_retry import ReviewRetryHistory, ReviewAIOperation, ReviewOperationKind, AIExecutionAttempt
    from core.ai.ai_request import AIRequest
    from test_classify_review_result import staged
    from uuid import uuid4
    import subprocess

    c, request, runner = routing_case
    if mode == 'STAGED':
        reviewed = staged(request.review.review)
        ref = 'review.stages.0.assessment.findings.0'
        report = replace(request.review.report, references=(ref, *request.review.report.references[1:]))
        request = replace(request, review=replace(request.review, review=reviewed, report=report),
                          problems=(replace(request.problems[0], finding_references=(ref,)),))
    operation = ReviewAIOperation(uuid4(), ReviewOperationKind.BATCH, AIRequest('original'), request.review.review)
    history = ReviewRetryHistory(operation, AIExecutionAttempt(execution_error='temporary'),
                                 AIExecutionAttempt(AIResponse('recovered', True)))
    request = replace(request, retry_history=(history,))
    snapshot = asdict(request)
    disk = {p: p.read_bytes() for p in c['request'].repository_path.iterdir() if p.is_file()}
    forbidden = Mock(side_effect=AssertionError('Target 7 execution is forbidden'))
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr('core.ai.codex_runner.CodexRunner.run', forbidden)
    monkeypatch.setattr('application.collect_implementation_evidence.CollectImplementationEvidenceUseCase.execute', forbidden)
    monkeypatch.setattr('application.state_transition.transition_state', forbidden)
    monkeypatch.setattr('application.technical_review_retry.TechnicalReviewRetryUseCase.execute', forbidden)
    output = PrepareCorrectionUseCase(AIService(runner)).execute(request)
    assert output.ready
    assert asdict(request) == snapshot
    assert output.request.retry_history[0] is history
    assert output.instructions[0].allowed_changes == c['evidence'].scope.allowed_changes
    assert output.instructions[0].forbidden_changes == c['evidence'].scope.forbidden_changes
    assert disk == {p: p.read_bytes() for p in disk}
    forbidden.assert_not_called()


@pytest.mark.parametrize('field', [
    'destination', 'problem', 'cause', 'targets', 'rationale', 'review_reference',
    'finding_references', 'basis_references', 'scope_reference', 'allowed_changes',
    'forbidden_changes', 'safe_scope_reasons', 'required_test_references', 'correction_references',
])
def test_each_required_instruction_field_is_validated(routing_case, field):
    from application.prepare_correction import PrepareCorrectionUseCase
    _, request, runner = routing_case
    def respond(ai_request):
        context = json.loads(ai_request.prompt.split('CORRECTION_INPUT\n', 1)[1])
        del context['instructions'][0][field]
        return AIResponse(json.dumps({'instructions': context['instructions']}), True)
    runner.run.side_effect = respond
    output = PrepareCorrectionUseCase(AIService(runner)).execute(request)
    assert not output.ready and output.validation_errors and not output.instructions


@pytest.mark.parametrize('field,reference', [
    ('correction_references', f'{BASE}.sources.0.content'),
    ('correction_references', 'review.prepared.mismatches.0'),
    ('required_test_references', 'review.prepared.mismatches.0'),
    ('required_test_references', f'{BASE}.evidence.verification.errors'),
])
def test_existing_but_unsuitable_references_do_not_authorize_instruction(routing_case, field, reference):
    from application.prepare_correction import PrepareCorrectionUseCase
    _, request, runner = routing_case
    request = replace(request, problems=(replace(request.problems[0], **{field: (reference,)}),))
    output = PrepareCorrectionUseCase(AIService(runner)).execute(request)
    assert output.blocked_reasons and not output.ready
    runner.run.assert_not_called()


def test_count_policy_is_supplied_by_caller_not_an_independent_limit_engine(routing_case):
    from application.prepare_correction import PrepareCorrectionUseCase
    _, request, runner = routing_case
    request = replace(request, control=replace(request.control, correction_count=100, count_condition_met=True))
    output = PrepareCorrectionUseCase(AIService(runner)).execute(request)
    assert output.ready and output.request.control.correction_count == 100


@pytest.mark.parametrize('change', [
    'approved', 'human', 'none', 'review_failure', 'execution_error', 'parse_error',
    'invalid_report', 'missing_report', 'missing_target', 'missing_cause',
    'missing_rationale', 'missing_references', 'missing_safe_scope',
    'human_questions', 'missing_state', 'missing_approval', 'missing_input',
    'destination', 'unknown_destination', 'scope', 'safe_scope', 'unsafe',
    'finding_reference', 'target', 'tests', 'correction_reference',
    'not_allowed', 'early_stop', 'count_missing', 'count_negative',
    'count_bool', 'count_disallowed', 'count_unconfirmed', 'stop_unknown',
    'allowed_unknown', 'no_problems', 'recovery_failed',
    'specification', 'plan', 'human_destination', 'critical',
])
def test_blocks_unestablished_or_unsafe_routing_before_ai(routing_case, change):
    from application.prepare_correction import PrepareCorrectionUseCase
    from application.review_retry import ReviewRetryHistory, ReviewAIOperation, ReviewOperationKind, AIExecutionAttempt
    from core.ai.ai_request import AIRequest
    from uuid import uuid4

    _, request, runner = routing_case
    report_changes = {
        'missing_target': {'targets': ()}, 'missing_cause': {'cause': ''},
        'missing_rationale': {'rationale': ''}, 'missing_references': {'references': ()},
        'missing_safe_scope': {'safe_scope_reason': ''}, 'human_questions': {'human_questions': ('Decide design',)},
    }
    problem_changes = {
        'destination': {'destination': None}, 'unknown_destination': {'destination': 'Source Code'},
        'scope': {'scope_reference': ''}, 'safe_scope': {'safe_scope_reason': ''},
        'unsafe': {'safe_in_scope': False}, 'finding_reference': {'finding_references': ('review.unknown',)},
        'target': {'targets': ('unapproved.py',)}, 'tests': {'required_test_references': ()},
        'correction_reference': {'correction_references': ('review.unknown',)},
        'specification': {'destination': 'Specification策定工程'}, 'plan': {'destination': 'Plan修正工程'},
        'human_destination': {'destination': 'Human判断'}, 'critical': {'destination': 'Critical Change Approval工程'},
    }
    controls = {
        'not_allowed': {'correction_allowed': False}, 'early_stop': {'early_stop_triggered': True},
        'count_missing': {'correction_count': None}, 'count_negative': {'correction_count': -1},
        'count_bool': {'correction_count': True}, 'count_disallowed': {'count_condition_met': False},
        'count_unconfirmed': {'count_condition_met': None}, 'stop_unknown': {'early_stop_triggered': None},
        'allowed_unknown': {'correction_allowed': None},
    }
    if change in report_changes:
        request = replace(request, review=replace(request.review, report=replace(request.review.report, **report_changes[change])))
    elif change in problem_changes:
        request = replace(request, problems=(replace(request.problems[0], **problem_changes[change]),))
    elif change in controls:
        request = replace(request, control=replace(request.control, **controls[change]))
    elif change in ('approved', 'human', 'none'):
        result = {'approved': ReviewResult.APPROVED, 'human': ReviewResult.HUMAN_REVIEW_REQUIRED, 'none': None}[change]
        request = replace(request, review=replace(request.review, result=result))
    elif change in ('review_failure', 'execution_error', 'parse_error', 'invalid_report', 'missing_report'):
        updates = {'review_failure': {'review_failures': ('Review failed',)},
                   'execution_error': {'execution_error': 'AI failed'}, 'parse_error': {'parse_error': 'Invalid JSON'},
                   'invalid_report': {'validation_errors': ('Invalid',)}, 'missing_report': {'report': None}}[change]
        request = replace(request, review=replace(request.review, **updates))
    elif change in ('missing_input', 'missing_approval'):
        prepared = request.review.review.prepared
        inp = None if change == 'missing_input' else replace(prepared.review_input, approval_records=())
        request = replace(request, review=replace(request.review, review=replace(request.review.review,
            prepared=replace(prepared, review_input=inp))))
    elif change == 'missing_state':
        request = replace(request, current_state=None)
    elif change == 'no_problems':
        request = replace(request, problems=())
    elif change == 'recovery_failed':
        operation = ReviewAIOperation(uuid4(), ReviewOperationKind.BATCH, AIRequest('same'), request.review.review)
        failure = AIExecutionAttempt(execution_error='Transient AI failure')
        request = replace(request, retry_history=(ReviewRetryHistory(operation, failure, failure),))
    output = PrepareCorrectionUseCase(AIService(runner)).execute(request)
    assert not output.ready
    assert output.instructions == ()
    assert output.blocked_reasons
    assert output.request is request
    runner.run.assert_not_called()


def add_finding(request, *, destination='Codex再実装工程', safe_group='approved-validation'):
    reviewed = request.review.review
    aspect = reviewed.batch.aspects[0]
    # Equal semantic values remain two distinct occurrences with distinct paths.
    aspect = replace(aspect, findings=(*aspect.findings, replace(aspect.findings[0])))
    reviewed = replace(reviewed, batch=replace(reviewed.batch, aspects=(aspect, *reviewed.batch.aspects[1:])))
    problem = replace(request.problems[0], destination=destination,
                      finding_references=('review.batch.aspects.0.findings.1',), safe_group=safe_group)
    return replace(request, review=replace(request.review, review=reviewed), problems=(*request.problems, problem))


@pytest.mark.parametrize('destination,group,count', [
    ('Codex再実装工程', 'approved-validation', 1),
    ('Test修正工程', 'approved-validation', 2),
    ('Prompt再生成工程', 'approved-validation', 2),
    ('Codex再実装工程', None, 2),
    ('Codex再実装工程', 'different-safe-group', 2),
])
def test_groups_only_explicitly_safe_same_destination_and_scope_without_dedup(routing_case, destination, group, count):
    from application.prepare_correction import PrepareCorrectionUseCase
    _, request, runner = routing_case
    request = add_finding(request, destination=destination, safe_group=group)
    output = PrepareCorrectionUseCase(AIService(runner)).execute(request)
    assert output.ready
    assert len(output.instructions) == count
    refs = tuple(ref for instruction in output.instructions for ref in instruction.finding_references)
    assert refs == (FINDING, 'review.batch.aspects.0.findings.1')
    originals = output.request.review.review.batch.aspects[0].findings
    assert len(originals) == 2 and originals[0] == originals[1]
    assert originals[0].rationale and originals[1].references and originals[1].origin == 'semantic'


@pytest.mark.parametrize('failure', ['unsafe', 'unknown_destination', 'scope', 'omitted_finding'])
def test_one_unroutable_problem_blocks_entire_set_without_changing_result(routing_case, failure):
    from application.prepare_correction import PrepareCorrectionUseCase
    _, request, runner = routing_case
    request = add_finding(request)
    if failure == 'omitted_finding':
        request = replace(request, problems=request.problems[:1])
    else:
        changes = {'unsafe': {'safe_in_scope': False}, 'unknown_destination': {'destination': None},
                   'scope': {'scope_reference': 'review.unapproved_scope'}}[failure]
        request = replace(request, problems=(request.problems[0], replace(request.problems[1], **changes)))
    output = PrepareCorrectionUseCase(AIService(runner)).execute(request)
    assert output.blocked_reasons and not output.instructions and not output.ready
    assert output.request.review is request.review
    assert output.request.review.result == ReviewResult.REVISION_REQUIRED
    runner.run.assert_not_called()


@pytest.mark.parametrize('failure', ['exception', 'unsuccessful', 'empty_error', 'json', 'duplicate', 'wrong_type',
    'missing_field', 'new_design', 'scope_expansion', 'changed_destination', 'changed_target', 'missing_instruction'])
def test_generation_failure_is_retained_without_retry_or_partial_instruction(routing_case, failure):
    from application.prepare_correction import PrepareCorrectionUseCase
    _, request, runner = routing_case
    request = add_finding(request, destination='Test修正工程')
    def respond(ai_request):
        if failure == 'exception':
            raise RuntimeError('Temporary failure')
        if failure in ('unsuccessful', 'empty_error'):
            return AIResponse('partial response', False, 'Temporary failure' if failure == 'unsuccessful' else None)
        if failure == 'json':
            return AIResponse('not json', True)
        if failure == 'duplicate':
            return AIResponse('{"instructions": [], "instructions": []}', True)
        if failure == 'wrong_type':
            return AIResponse('{"instructions": "none"}', True)
        context = json.loads(ai_request.prompt.split('CORRECTION_INPUT\n', 1)[1])
        items = context['instructions']
        if failure == 'missing_field':
            del items[1]['required_test_references']
        elif failure == 'new_design':
            items[1]['implementation_method'] = 'Introduce a new database'
        elif failure == 'scope_expansion':
            items[1]['allowed_changes'] = ['*']
        elif failure == 'changed_destination':
            items[1]['destination'] = 'Specification策定工程'
        elif failure == 'changed_target':
            items[1]['targets'] = ['new_database.py']
        elif failure == 'missing_instruction':
            items.pop()
        return AIResponse(json.dumps({'instructions': items}), True)
    runner.run.side_effect = respond
    output = PrepareCorrectionUseCase(AIService(runner)).execute(request)
    assert not output.ready and output.instructions == ()
    if failure in ('exception', 'unsuccessful', 'empty_error'):
        assert output.execution_error and not output.parse_error
    elif failure in ('json', 'duplicate', 'wrong_type'):
        assert output.parse_error and not output.execution_error
    else:
        assert output.validation_errors and not output.parse_error and not output.execution_error
    assert output.request is request
    runner.run.assert_called_once()
