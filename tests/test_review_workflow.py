import json
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from test_plan_workflow import flow
from test_implementation_workflow import implementation
from test_evidence_workflow import evidence_flow
from test_review_implementation import response
from test_classify_review_result import evaluation, resolution
from application.review_retry import RetryAuthorization
from application.review_with_retry import ReviewWithRetryUseCase
from core.ai.ai_response import AIResponse
from core.ai.ai_service import AIService
from infrastructure.git_repository_state_provider import GitRepositoryStateProvider
from infrastructure.json_test_state_provider import JsonTestStateProvider


def approved_response(request):
    context = json.loads(request.prompt.split('# Result Input\n', 1)[1])
    data = evaluation('APPROVED')
    data.update(problem='', cause='', targets=[], safe_scope_reason='',
                references=['review.prepared.review_input.specification.content'])
    data['checks'] = {key: dict(confirmed=True, rationale='Confirmed against approved artifacts',
        references=['review.prepared.review_input.specification.content'])
        for key in ('specification', 'plan', 'scope', 'no_major_issues', 'tests_executed', 'test_behavior')}
    data['resolutions'] = [resolution(ref) for ref in context['concerns']]
    return AIResponse(json.dumps(data), True)


@pytest.fixture
def review_flow(evidence_flow):
    from application.review_workflow import ReviewWorkflowInput, ReviewWorkflowUseCase
    case = evidence_flow
    upstream = case.use_case.execute(case.evidence_request)
    assert upstream.success, upstream.stop_reason
    runner = Mock()
    def run(request):
        assert json.loads(case.flow.state.read_text())['status'] == 'reviewing'
        transitions = [json.loads(p.read_text()) for p in case.flow.history.glob('*.json')]
        assert any(t['from_state'] == 'implementation_completed' and t['to_state'] == 'reviewing' for t in transitions)
        if request.prompt.startswith('# Review Result Evaluation'):
            return approved_response(request)
        return AIResponse(json.dumps(response()), True)
    runner.run.side_effect = run
    authorize = Mock(return_value=RetryAuthorization())
    reviewer = ReviewWithRetryUseCase(AIService(runner), authorize)
    use_case = ReviewWorkflowUseCase(case.flow.repo, case.repository,
        GitRepositoryStateProvider, JsonTestStateProvider, reviewer)
    request = ReviewWorkflowInput(upstream, 'BATCH', case.flow.tmp_path / 'review_artifacts')
    return SimpleNamespace(**locals())


def test_complete_review_handoff_starts_review_and_prepares_phase6_handoff_when_approved(review_flow):
    c = review_flow
    before = {p: p.read_bytes() for p in c.case.flow.repo.approvals_dir.glob('*.json')}
    result = c.use_case.start(c.request)
    assert result.success, (result.stop_reason, result.review.classification.execution_error,
                           result.review.classification.parse_error, result.review.classification.validation_errors,
                           result.review.classification.review_failures)
    assert result.review.classification.result == 'APPROVED'
    assert result.handoff.handoff_type == 'PHASE_6'
    assert result.ready_for_final_approval
    assert not result.waiting_for_human
    assert result.current_state['status'] == 'reviewing'
    assert result.handoff.current_state == 'reviewing'
    assert result.correction_count == 0
    assert result.artifact_paths[-1].is_file()
    assert json.loads(result.artifact_paths[-1].read_text(encoding='utf-8'))['handoff']['handoff_type'] == 'PHASE_6'
    assert c.runner.run.call_count == 2
    c.authorize.assert_not_called()
    assert {p: p.read_bytes() for p in before} == before


@pytest.mark.parametrize('mode', ['failed', 'stopped', 'missing', 'incomplete', 'evidence', 'identity', 'state', 'mode', 'changed_source'])
def test_invalid_start_never_runs_review(review_flow, mode):
    c = review_flow
    request, upstream = c.request, c.upstream
    if mode == 'failed':
        upstream = replace(upstream, success=False)
    elif mode == 'stopped':
        upstream = replace(upstream, stop_reason='Stopped')
    elif mode == 'missing':
        upstream = replace(upstream, handoff=None)
    elif mode == 'incomplete':
        upstream = replace(upstream, handoff=replace(upstream.handoff, missing_information=('tests',)))
    elif mode == 'evidence':
        upstream.collection.evidence_path.unlink()
    elif mode == 'identity':
        upstream = replace(upstream, collection=replace(upstream.collection, implementation_id=None))
    elif mode == 'state':
        c.case.flow.state.write_text('{"status": "cancelled"}')
    elif mode == 'mode':
        request = replace(request, mode=None)
    else:
        (c.case.request.repository / 'source.py').write_text('changed after Target 4')
    before = c.case.flow.state.read_bytes()
    result = c.use_case.start(replace(request, upstream=upstream))
    assert not result.success and result.stop_reason
    assert c.case.flow.state.read_bytes() == before
    c.runner.run.assert_not_called()


@pytest.mark.parametrize('part', ['state', 'history'])
def test_start_persistence_failure_prevents_review_and_preserves_actual_state(review_flow, monkeypatch, part):
    c = review_flow
    name = 'save_current_state' if part == 'state' else 'save_state_transition_history'
    monkeypatch.setattr('application.state_transition.' + name, Mock(side_effect=OSError('disk full')))
    result = c.use_case.start(c.request)
    assert not result.success and result.transition
    assert result.current_state['status'] == ('implementation_completed' if part == 'state' else 'reviewing')
    assert result.stop_reason
    c.runner.run.assert_not_called()


@pytest.mark.parametrize('result_name', ['HUMAN_REVIEW_REQUIRED', 'REVISION_REQUIRED'])
def test_human_waiting_and_missing_correction_inputs_never_start_correction(review_flow, result_name):
    c = review_flow
    original = c.runner.run.side_effect
    def run(request):
        if request.prompt.startswith('# Review Result Evaluation'):
            data = evaluation(result_name)
            data['references'] = ['review.prepared.review_input.implementation_plan.content']
            if result_name == 'HUMAN_REVIEW_REQUIRED':
                data['human_questions'] = ['Human must clarify the required behavior']
            return AIResponse(json.dumps(data), True)
        return original(request)
    c.runner.run.side_effect = run
    result = c.use_case.start(c.request)
    assert result.success and result.waiting_for_human
    assert not result.ready_for_final_approval
    assert result.current_state['status'] == 'reviewing'
    assert result.handoff.handoff_type == 'HUMAN_REVIEW'
    assert result.review.classification.result == result_name
    assert result.correction_count == 0
    c.case.runner.run.assert_called_once()  # Only the original Implementation.


@pytest.mark.parametrize('mode', ['execution', 'parse', 'classification', 'invalid_approval'])
def test_review_failures_are_not_success_or_final_approval(review_flow, mode):
    c = review_flow
    original = c.runner.run.side_effect
    def run(request):
        classify = request.prompt.startswith('# Review Result Evaluation')
        if mode == 'execution':
            return AIResponse('', False, 'transport failure')
        if mode == 'parse' or (mode == 'classification' and classify):
            return AIResponse('not json', True)
        if mode == 'invalid_approval' and classify:
            data = json.loads(approved_response(request).content)
            data['unresolved'] = ['An unresolved issue remains']
            return AIResponse(json.dumps(data), True)
        return original(request)
    c.runner.run.side_effect = run
    result = c.use_case.start(c.request)
    assert not result.success and result.stop_reason
    assert not result.ready_for_final_approval
    assert result.review.classification.result is None
    assert result.artifact_paths[-1].exists()
    assert result.current_state['status'] == 'review_failed'


def test_review_snapshot_failure_is_not_success(review_flow, monkeypatch):
    from pathlib import Path
    c = review_flow
    original = Path.open
    def fail(path, *args, **kwargs):
        if path.name.startswith('review_workflow_'):
            raise OSError('Review snapshot cannot be saved')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', fail)
    result = c.use_case.start(c.request)
    assert not result.success and 'persistence failed' in result.stop_reason
    assert result.handoff.handoff_type == 'PHASE_6'
    assert not result.ready_for_final_approval


def test_target_six_and_approval_writers_are_never_called(review_flow, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('Target 6 / Human Approval must not run')
    monkeypatch.setattr('application.final_approval_entry.FinalApprovalEntryUseCase.execute', forbidden)
    monkeypatch.setattr('application.final_approval_target.FinalApprovalTargetUseCase.execute', forbidden)
    monkeypatch.setattr(review_flow.case.flow.repo, 'save', forbidden)
    assert review_flow.use_case.start(review_flow.request).ready_for_final_approval


@pytest.fixture
def correction_flow(review_flow):
    from application.codex_execution import CodexCommandEvent, CodexJsonlParseResult
    from application.correction_continuation import ExistingAssessment, EarlyStopCondition
    from application.correction_routing import CorrectionProblem
    from application.correction_cycle import ReTestPlan
    from application.execute_correction_cycle import ExecuteCorrectionCycleUseCase
    from application.prepare_correction import PrepareCorrectionUseCase
    from infrastructure.json_test_execution_recorder import JsonTestExecutionRecorder
    from infrastructure.json_test_execution_record_repository import JsonTestExecutionRecordRepository
    from infrastructure.json_command_trace_repository import JsonCommandTraceRepository
    from test_correction_cycle import report

    c = review_flow
    # This scenario supplies complete recorded Test facts. The ordinary initial
    # fixture intentionally leaves fields unavailable and must stop instead.
    record_path = c.case.upstream.execution.test_execution_record_path
    record = json.loads(record_path.read_text(encoding='utf-8'))
    record.update(unavailable_evidence=[], tests_created_or_modified=['test_source.py'])
    record_path.write_text(json.dumps(record), encoding='utf-8')
    tests = JsonTestStateProvider(record_path=record_path,
        expected_implementation_id=c.case.request.implementation_id).get_state()
    initial = replace(c.case.upstream, test_state=tests)
    target4 = c.case.use_case.execute(replace(c.case.evidence_request, upstream=initial))
    assert target4.success, target4.stop_reason
    c.request = replace(c.request, upstream=target4)
    calls = []
    def review(request):
        corrected = 'retest' in calls
        if request.prompt.startswith('# Review Result Evaluation'):
            if corrected:
                return approved_response(request)
            return AIResponse(json.dumps(evaluation()), True)
        data = response()
        if not corrected:
            data['aspects'][0]['findings'] = [dict(description='Missing validation', rationale='Required by Plan',
                references=['review_input.implementation_plan.content'])]
        return AIResponse(json.dumps(data), True)
    c.runner.run.side_effect = review
    first = c.use_case.start(c.request)
    assert first.success and first.review.classification.result == 'REVISION_REQUIRED'
    adapter = Mock()
    def run(*, prompt, working_directory):
        context, _ = json.JSONDecoder().raw_decode(prompt.rsplit('CORRECTION CYCLE CONTEXT:\n', 1)[1].lstrip())
        if context['operation'] == 'RE_TEST_ONLY':
            calls.append('retest')
            events = tuple(CodexCommandEvent(i + 1, str(i), command, 'completed', 0, 'passed', phase)
                for i, (command, phase) in enumerate((('target-test', 'target'), ('required-test', 'target'),
                    ('existing-test', 'target'), ('full-test', 'full'))))
            return CodexJsonlParseResult('', events, report('COMPLETED', 'PASS'), True, ())
        calls.append('correction')
        (working_directory / 'source.py').write_text('value = 2\n', encoding='utf-8')
        return CodexJsonlParseResult('', (CodexCommandEvent(1, 'initial', 'initial-test', 'completed', 1, 'failed', 'initial'),),
                                    report(), True, ())
    adapter.run.side_effect = run
    routing_ai = Mock()
    routing_ai.run.side_effect = lambda request: AIResponse(json.dumps({'instructions':
        json.loads(request.prompt.split('CORRECTION_INPUT\n', 1)[1])['instructions']}), True)
    directory = c.request.artifact_dir / 'cycles'
    recorder = JsonTestExecutionRecorder(trace_repository=JsonCommandTraceRepository(directory),
        record_repository=JsonTestExecutionRecordRepository(directory))
    cycle = ExecuteCorrectionCycleUseCase(adapter=adapter, recorder=recorder,
        evidence_repository=c.case.repository, repository_state_provider=GitRepositoryStateProvider(c.case.request.repository),
        approval_repository=c.case.flow.repo, test_state_provider_factory=lambda path, identity: JsonTestStateProvider(
            record_path=path, expected_implementation_id=identity), ai_service=AIService(c.runner))
    c.use_case._correction_preparer = PrepareCorrectionUseCase(AIService(routing_ai))
    c.use_case._correction_cycle = cycle
    base = 'review.prepared.review_input'
    problems = (CorrectionProblem('Codex再実装工程', ('source.py',), ('review.batch.aspects.0.findings.0',),
        base + '.evidence.scope', True, 'Explicit existing Plan requirement',
        (base + '.evidence.verification.test_commands',), (base + '.implementation_plan.content',)),)
    assessments = (ExistingAssessment(EarlyStopCondition.SAFE_CONTINUATION, True, 'Existing Review confirms safe scope',
                                     ('review.report.safe_scope_reason',)),)
    retest = ReTestPlan(('target-test',), ('required-test',), ('existing-test',), ('full-test',), True)
    return SimpleNamespace(**locals())


def test_explicit_correction_retests_and_hands_off_new_evidence_after_rereview(correction_flow):
    from application.review_workflow import CorrectionStepInput
    c = correction_flow
    old = c.first.review.review.prepared.review_input.evidence
    old_bytes = c.target4.collection.evidence_path.read_bytes()
    step = CorrectionStepInput(c.first.review.classification, c.assessments, c.problems, c.retest)
    output = c.c.use_case.correct(c.first, step)
    assert output.success, output.stop_reason
    assert c.calls == ['correction', 'retest']
    assert output.ready_for_final_approval
    assert output.correction_count == 1
    assert output.current_state['status'] == 'reviewing'
    cycle = output.cycles[-1]
    new = cycle.evidence.implementation_evidence
    assert new.identity.implementation_id != old.identity.implementation_id
    assert new.identity.evidence_id != old.identity.evidence_id
    assert new.identity.previous_evidence_id == old.identity.evidence_id
    assert new.basis.implementation_plan_path == old.basis.implementation_plan_path
    assert new.basis.codex_prompt_path != old.basis.codex_prompt_path
    assert new.identity.base_commit == old.identity.base_commit
    assert output.handoff.request.implementation_id == new.identity.implementation_id
    assert output.review is cycle.re_review
    assert c.target4.collection.evidence_path.read_bytes() == old_bytes
    assert cycle.history_path.is_file()
    assert output.artifact_paths[-1].is_file()


@pytest.mark.parametrize('missing', ['safety', 'problems', 'tests', 'test_commands', 'review_identity', 'approval', 'destination'])
def test_correction_requires_current_explicit_conditions(correction_flow, missing):
    from application.review_workflow import CorrectionStepInput
    c = correction_flow
    step = CorrectionStepInput(c.first.review.classification, c.assessments, c.problems, c.retest)
    if missing == 'safety':
        step = replace(step, assessments=())
    elif missing == 'problems':
        step = replace(step, problems=())
    elif missing == 'tests':
        step = replace(step, tests=None)
    elif missing == 'test_commands':
        step = replace(step, tests=replace(c.retest, target_commands=()))
    elif missing == 'review_identity':
        step = replace(step, review=replace(step.review, raw_response='different Review'))
    elif missing == 'approval':
        (c.c.case.flow.repo.approvals_dir / 'plan-1.json').unlink()
    else:
        step = replace(step, problems=(replace(c.problems[0], destination='Test修正工程'),))
    result = c.c.use_case.correct(c.first, step)
    assert not result.ready_for_final_approval
    assert result.waiting_for_human or (not result.success and result.stop_reason)
    assert result.current_state['status'] == 'reviewing'
    c.adapter.run.assert_not_called()


def test_explicit_early_stop_prevents_correction(correction_flow):
    from application.review_workflow import CorrectionStepInput
    from application.correction_continuation import ExistingAssessment, EarlyStopCondition
    c = correction_flow
    assessment = ExistingAssessment(EarlyStopCondition.SPECIFICATION_UNCERTAINTY, True,
        'Existing Review requires Specification judgment', ('review.report.problem',))
    result = c.c.use_case.correct(c.first, CorrectionStepInput(c.first.review.classification,
        (assessment,), c.problems, c.retest))
    assert result.waiting_for_human and result.continuation.decision == 'STOPPED'
    c.adapter.run.assert_not_called()


def test_recorded_correction_limit_routes_to_human_without_execution(correction_flow):
    c = correction_flow
    # Exercise the existing continuation limit at the integration routing boundary.
    # Actual Cycle execution and count increment are covered by the end-to-end test.
    output = c.c.use_case._route(replace(c.first, correction_count=3))
    assert output.success and output.waiting_for_human
    assert output.continuation.decision == 'STOPPED'
    assert output.continuation.reasons[0].code == 'MAX_CORRECTION_COUNT_REACHED'
    assert output.correction_count == 3
    assert not output.ready_for_final_approval
    c.adapter.run.assert_not_called()


def test_fabricated_correction_count_cannot_start_execution(correction_flow):
    from application.review_workflow import CorrectionStepInput
    c = correction_flow
    result = c.c.use_case.correct(replace(c.first, correction_count=1),
        CorrectionStepInput(c.first.review.classification, c.assessments, c.problems, c.retest))
    assert not result.success and 'Count' in result.stop_reason
    c.adapter.run.assert_not_called()



def test_staged_mode_uses_existing_five_stages_then_classification(review_flow):
    from test_semantic_staged_review import answer, context
    c = review_flow
    c.runner.run.side_effect = lambda request: (approved_response(request)
        if request.prompt.startswith('# Review Result Evaluation') else answer(context(request)['stage']))
    result = c.use_case.start(replace(c.request, mode='STAGED'))
    assert result.ready_for_final_approval, result.stop_reason
    assert c.runner.run.call_count == 6


def test_safe_technical_retry_does_not_start_or_count_correction(review_flow):
    c = review_flow
    original = c.runner.run.side_effect
    attempts = []
    def run(request):
        attempts.append(request)
        return AIResponse('', False, 'temporary failure') if len(attempts) == 1 else original(request)
    c.runner.run.side_effect = run
    c.authorize.return_value = RetryAuthorization(True, True, True, True, False, 'Caller verified same safe operation')
    result = c.use_case.start(c.request)
    assert result.ready_for_final_approval, result.stop_reason
    assert result.correction_count == 0 and not result.cycles
    assert attempts[0] == attempts[1]
    assert result.review.history[0].retry is not None


@pytest.mark.parametrize('part', ['state', 'history'])
def test_correction_start_persistence_failure_prevents_execution(correction_flow, monkeypatch, part):
    from application.review_workflow import CorrectionStepInput
    c = correction_flow
    name = 'save_current_state' if part == 'state' else 'save_state_transition_history'
    monkeypatch.setattr('application.state_transition.' + name, Mock(side_effect=OSError('disk full')))
    result = c.c.use_case.correct(c.first, CorrectionStepInput(c.first.review.classification,
        c.assessments, c.problems, c.retest))
    assert not result.success and result.stop_reason
    assert result.current_state['status'] == ('reviewing' if part == 'state' else 'correction_requested')
    assert result.routing.ready and result.transition
    c.adapter.run.assert_not_called()


def test_failed_correction_retains_cycle_diagnostics_and_does_not_handoff(correction_flow):
    from application.review_workflow import CorrectionStepInput
    c = correction_flow
    c.adapter.run.side_effect = RuntimeError('Runner unavailable')
    result = c.c.use_case.correct(c.first, CorrectionStepInput(c.first.review.classification,
        c.assessments, c.problems, c.retest))
    assert not result.success and result.stop_reason
    assert not result.ready_for_final_approval
    assert len(result.cycles) == 1 and result.cycles[0].failures
    assert result.artifact_paths[-1].is_file()
    assert result.correction_count == 0


def test_concurrent_state_change_is_observed_without_rollback(review_flow):
    c = review_flow
    original = c.runner.run.side_effect
    def run(request):
        result = original(request)
        if request.prompt.startswith('# Review Result Evaluation'):
            c.case.flow.state.write_text('{"status": "cancelled"}')
        return result
    c.runner.run.side_effect = run
    result = c.use_case.start(c.request)
    assert not result.success and not result.ready_for_final_approval
    assert result.current_state['status'] == 'cancelled'
    assert json.loads(c.case.flow.state.read_text())['status'] == 'cancelled'
