import hashlib
import json
from dataclasses import replace
from uuid import uuid4
from unittest.mock import Mock

import pytest

from test_plan_workflow import flow, approve_draft
from test_execute_to_test_state_e2e import JsonlCodexRunner
from test_git_repository_state_provider import make_clean_repository, run_git
from application.implementation_workflow import (
    ImplementationWorkflowInput, ImplementationWorkflowUseCase, InitialTddApplicability,
)
from application.codex_implementation_adapter import CodexImplementationAdapter
from application.execute_implementation import ExecuteImplementationUseCase
from infrastructure.git_implementation_preparation import GitImplementationPreparation
from infrastructure.codex_jsonl_parser import parse_codex_jsonl
from infrastructure.json_command_trace_repository import JsonCommandTraceRepository
from infrastructure.json_test_execution_record_repository import JsonTestExecutionRecordRepository
from infrastructure.json_test_execution_recorder import JsonTestExecutionRecorder
from infrastructure.json_test_state_provider import JsonTestStateProvider


@pytest.fixture
def implementation(flow):
    upstream = flow.use_case.generate_prompt(approve_draft(flow), flow.prompt)
    repo, base = make_clean_repository(flow.tmp_path)
    record = upstream.approval_result.approval_record
    tdd = InitialTddApplicability(
        flow.plan_path, record['approval_id'], record['artifact_hash'],
        hashlib.sha256(upstream.prompt_result.codex_prompt.encode('utf-8')).hexdigest(), True,
    )
    request = ImplementationWorkflowInput(upstream, uuid4(), repo, 'impl/initial', tdd)
    runner = Mock()
    runner.run.side_effect = JsonlCodexRunner().run
    recorder = JsonTestExecutionRecorder(
        trace_repository=JsonCommandTraceRepository(flow.tmp_path / 'records'),
        record_repository=JsonTestExecutionRecordRepository(flow.tmp_path / 'records'),
    )
    execution = ExecuteImplementationUseCase(flow.repo, CodexImplementationAdapter(runner, trace_parser=parse_codex_jsonl), recorder)
    preparation = GitImplementationPreparation()
    use_case = ImplementationWorkflowUseCase(flow.repo, preparation, execution, JsonTestStateProvider)
    return flow, request, runner, use_case, base


def test_approved_prompt_prepares_branch_and_base_before_implementation(implementation):
    flow, request, runner, use_case, base = implementation
    def run(**kwargs):
        assert run_git(request.repository, 'branch', '--show-current') == 'impl/initial'
        assert run_git(request.repository, 'rev-parse', 'HEAD') == base
        assert request.upstream.prompt_result.codex_prompt in kwargs['prompt']
        assert '"tdd_required": true' in kwargs['prompt']
        return JsonlCodexRunner().run(**kwargs)
    runner.run.side_effect = run

    result = use_case.execute(request)

    assert result.success, result.stop_reason
    assert result.prepared.base_commit == base
    assert result.execution.success
    assert result.test_state.initial_test_result == 'FAIL'
    assert result.test_state.target_test_result == 'PASS'
    assert result.test_state.full_test_result == 'PASS'
    assert result.current_state['status'] == 'implementation_completed'
    assert run_git(request.repository, 'rev-parse', 'developer') == base
    assert result.execution.test_execution_record_path.exists()
    runner.run.assert_called_once()


def assert_not_started(request, runner):
    runner.run.assert_not_called()
    assert run_git(request.repository, 'branch', '--show-current') == 'developer'
    assert not run_git(request.repository, 'branch', '--list', request.implementation_branch)


@pytest.mark.parametrize(('required', 'reason'), [
    (None, None), ('true', None), (1, None), (False, None), (False, ''),
    (False, '   '), (True, 'documentation-only'),
])
def test_tdd_applicability_must_be_explicit_and_consistent(implementation, required, reason):
    _, request, runner, use_case, _ = implementation
    request = replace(request, tdd=replace(request.tdd, tdd_required=required, no_tdd_reason=reason))
    result = use_case.execute(request)
    assert not result.success
    assert_not_started(request, runner)


@pytest.mark.parametrize('field', ['plan_path', 'plan_approval_id', 'plan_hash', 'prompt_hash'])
def test_tdd_input_must_bind_to_approved_identity(implementation, field):
    flow, request, runner, use_case, _ = implementation
    value = flow.tmp_path / 'other.md' if field == 'plan_path' else 'different'
    request = replace(request, tdd=replace(request.tdd, **{field: value}))
    result = use_case.execute(request)
    assert not result.success and 'not bound' in result.stop_reason
    assert_not_started(request, runner)


@pytest.mark.parametrize('mode', ['failed', 'pending', 'unusable', 'changed_plan', 'changed_prompt', 'missing_approval'])
def test_target_two_failure_or_invalid_identity_prevents_git_and_runner(implementation, mode):
    flow, request, runner, use_case, _ = implementation
    upstream = request.upstream
    if mode == 'failed':
        upstream = replace(upstream, success=False)
    elif mode == 'pending':
        upstream = replace(upstream, approval_result=None)
    elif mode == 'unusable':
        upstream = replace(upstream, prompt_result=replace(upstream.prompt_result, prompt_usable=False))
    elif mode == 'changed_plan':
        flow.plan_path.write_text('Changed after Human Approval')
    elif mode == 'changed_prompt':
        upstream = replace(upstream, prompt_result=replace(upstream.prompt_result,
            codex_prompt=upstream.prompt_result.codex_prompt + '\nUnapproved change'))
    else:
        (flow.repo.approvals_dir / 'plan-1.json').unlink()
    request = replace(request, upstream=upstream)
    assert not use_case.execute(request).success
    assert_not_started(request, runner)


def mutate_trace(runner, transform):
    original = JsonlCodexRunner().run(prompt='', working_directory=None)
    events = [json.loads(line) for line in original.splitlines()]
    transform(events)
    runner.run.side_effect = None
    runner.run.return_value = '\n'.join(json.dumps(event) for event in events)


def alter_phase(events, phase, exit_code):
    for event in events:
        item = event.get('item', {})
        if f'--phase {phase} ' in item.get('command', ''):
            item['exit_code'] = exit_code


@pytest.mark.parametrize('mode', ['initial_pass', 'target_fail', 'full_fail', 'missing_initial', 'wrong_order'])
def test_final_runner_success_does_not_prove_test_or_tdd_success(implementation, mode):
    _, request, runner, use_case, _ = implementation
    def alter(events):
        if mode == 'initial_pass':
            alter_phase(events, 'initial', 0)
        elif mode == 'target_fail':
            alter_phase(events, 'target', 1)
        elif mode == 'full_fail':
            alter_phase(events, 'full', 1)
        elif mode == 'missing_initial':
            events[:] = [e for e in events if '--phase initial ' not in e.get('item', {}).get('command', '')]
        else:
            events[2], events[3] = events[3], events[2]
    mutate_trace(runner, alter)
    result = use_case.execute(request)
    assert not result.success
    assert result.execution.success  # Execution and test/TDD facts remain distinct.
    assert result.test_state is not None
    assert result.current_state['status'] == 'implementation_completed'
    assert result.stop_reason


def test_non_tdd_reason_is_explicit_and_does_not_disable_tests(implementation):
    _, request, runner, use_case, _ = implementation
    request = replace(request, tdd=replace(request.tdd, tdd_required=False, no_tdd_reason='Human: comments only'))
    mutate_trace(runner, lambda events: alter_phase(events, 'initial', 0))
    result = use_case.execute(request)
    assert result.success, result.stop_reason
    assert result.test_state.no_tdd_reason == 'Human: comments only'
    assert result.execution.implementation_result.test_required is True
    assert '"tdd_required": false' in runner.run.call_args.kwargs['prompt']
    data = json.loads(result.execution.test_execution_record_path.read_text())
    assert data['no_tdd_reason'] == 'Human: comments only'


def test_non_tdd_still_stops_on_required_test_failure(implementation):
    _, request, runner, use_case, _ = implementation
    request = replace(request, tdd=replace(request.tdd, tdd_required=False, no_tdd_reason='Human: formatting only'))
    mutate_trace(runner, lambda events: alter_phase(events, 'target', 1))
    assert not use_case.execute(request).success


def test_runner_test_required_no_cannot_override_explicit_tdd(implementation):
    _, request, runner, use_case, _ = implementation
    def alter(events):
        alter_phase(events, 'initial', 0)
        for event in events:
            item = event.get('item', {})
            if 'text' in item:
                item['text'] = item['text'].replace('TEST_REQUIRED: YES', 'TEST_REQUIRED: NO')
    mutate_trace(runner, alter)
    result = use_case.execute(request)
    assert not result.success and 'Initial FAIL' in result.stop_reason
    assert result.execution.implementation_result.test_required is False


@pytest.mark.parametrize('mode', ['runner_error', 'critical_change', 'unsafe_retry'])
def test_existing_execution_stop_boundaries_are_preserved(implementation, mode):
    _, request, runner, use_case, _ = implementation
    if mode == 'runner_error':
        runner.run.side_effect = RuntimeError('timeout; retry suggested by error text')
    else:
        def alter(events):
            for event in events:
                item = event.get('item', {})
                if 'text' not in item:
                    continue
                if mode == 'critical_change':
                    item['text'] = item['text'].replace('## Human Approval Required\nNONE', '## Human Approval Required\nScope expansion needs Human')
                else:
                    item['text'] = item['text'].replace('## Test Execution Status\nCOMPLETED', '## Test Execution Status\nERROR').replace('## Test Result\nPASS', '## Test Result\nNONE')
        mutate_trace(runner, alter)
    result = use_case.execute(request)
    assert not result.success
    assert result.execution is not None and not result.execution.success
    runner.run.assert_called_once()
    if mode == 'critical_change':
        assert result.execution.critical_change_required
        assert result.current_state['status'] == 'critical_approval_pending'
    else:
        assert result.current_state['status'] == 'implementation_failed'


@pytest.mark.parametrize('mode', ['invalid_state', 'state_load', 'state_save', 'history_save'])
def test_state_failures_do_not_claim_implementation_success(implementation, monkeypatch, mode):
    import application.state_transition as persistence
    flow, request, runner, use_case, _ = implementation
    if mode == 'invalid_state':
        flow.state.write_text('{"status": "plan_approval_pending"}')
    elif mode == 'state_load':
        flow.state.write_text('invalid json')
    else:
        method = 'save_current_state' if mode == 'state_save' else 'save_state_transition_history'
        monkeypatch.setattr(persistence, method, Mock(side_effect=OSError(method)))
    result = use_case.execute(request)
    assert not result.success
    runner.run.assert_not_called()
    if mode == 'history_save':
        assert result.current_state['status'] == 'implementing'
    elif mode == 'state_load':
        assert result.current_state is None


@pytest.mark.parametrize('mode', ['not_repository', 'missing_base', 'dirty', 'existing_branch', 'branch_failure'])
def test_preparation_failure_never_starts_runner(implementation, monkeypatch, mode):
    import infrastructure.git_implementation_preparation as preparation
    flow, request, runner, use_case, _ = implementation
    if mode == 'not_repository':
        request = replace(request, repository=flow.tmp_path)
    elif mode == 'missing_base':
        run_git(request.repository, 'branch', '-m', 'other')
    elif mode == 'dirty':
        (request.repository / 'tracked.txt').write_text('Local changes')
    elif mode == 'existing_branch':
        run_git(request.repository, 'branch', request.implementation_branch)
    else:
        original = preparation.subprocess.run
        def fail_checkout(args, **kwargs):
            if args[1] == 'checkout':
                raise OSError('Branch creation failed')
            return original(args, **kwargs)
        monkeypatch.setattr(preparation.subprocess, 'run', fail_checkout)
    result = use_case.execute(request)
    assert not result.success
    runner.run.assert_not_called()
    assert json.loads(flow.state.read_text())['status'] == 'implementation_ready'


@pytest.mark.parametrize(('save_method', 'observed_status'), [
    ('save_state_transition_history', 'implementation_completed'),
    ('save_current_state', 'implementing'),
])
def test_final_history_failure_retains_implementation_and_test_facts(implementation, monkeypatch, save_method, observed_status):
    import application.state_transition as persistence
    _, request, runner, use_case, _ = implementation
    save = getattr(persistence, save_method)
    def fail_final(path, data):
        if data.get('to_state', data.get('status')) == 'implementation_completed':
            raise OSError(f'Final {save_method} failed')
        save(path, data)
    monkeypatch.setattr(persistence, save_method, fail_final)
    result = use_case.execute(request)
    assert not result.success
    assert result.execution.implementation_result is not None
    assert not result.execution.success
    assert save_method in result.execution.error_message
    assert result.execution.test_execution_record_path.exists()
    assert result.test_state.full_test_result == 'PASS'
    assert result.current_state['status'] == observed_status
    assert result.execution.current_state == observed_status
    runner.run.assert_called_once()


def test_safe_technical_retry_preserves_prompt_and_explicit_tdd_input(implementation):
    flow, request, runner, use_case, _ = implementation
    success = JsonlCodexRunner().run(prompt='', working_directory=None)
    failed = success.replace('## Changed Files\\napplication/example.py', '## Changed Files\\nNONE')
    failed = failed.replace('## Test Execution Status\\nCOMPLETED', '## Test Execution Status\\nERROR')
    failed = failed.replace('## Test Result\\nPASS', '## Test Result\\nNONE')
    failed = failed.replace('TECHNICAL_RETRY_SAFE: NO', 'TECHNICAL_RETRY_SAFE: YES')
    failed = failed.replace('TECHNICAL_RETRY_OPERATION: NONE', 'TECHNICAL_RETRY_OPERATION: python -m pytest')
    runner.run.side_effect = [failed, success]
    result = use_case.execute(request)
    assert result.success, result.stop_reason
    assert runner.run.call_count == 2
    assert runner.run.call_args_list[0] == runner.run.call_args_list[1]
    assert 'correction_count' not in json.loads(flow.state.read_text())
