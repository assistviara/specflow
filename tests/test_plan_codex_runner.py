import json
from unittest.mock import Mock

import pytest

from core.ai.ai_request import AIRequest
from infrastructure.plan_codex_runner import PlanCodexRunner
from infrastructure.plan_repository_snapshot import PlanRepositorySnapshotProvider, SnapshotUnavailable
from test_git_repository_state_provider import make_clean_repository


def completed(body='# Plan'):
    return '\n'.join(json.dumps(event) for event in [
        {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': body}},
        {'type': 'turn.completed'},
    ])


@pytest.fixture
def runner(tmp_path):
    root, _ = make_clean_repository(tmp_path)
    executor = Mock()
    executor.run.return_value = completed()
    validator = Mock()
    snapshots = Mock(wraps=PlanRepositorySnapshotProvider(root))
    return PlanCodexRunner(executor, root, validator, snapshots), executor, root, snapshots, validator


def test_read_only_fixed_cwd_stdin_and_final_body(runner):
    plan, executor, root, snapshots, validator = runner
    result = plan.run(AIRequest('requested plan'))
    assert result.success and result.content == '# Plan'
    command = executor.run.call_args.args[0]
    assert command == ['codex', '--ask-for-approval', 'never', 'exec', '--sandbox',
                       'read-only', '--json', '--ephemeral', '-']
    assert executor.run.call_args.kwargs['cwd'] == root
    assert executor.run.call_args.kwargs['input_text'].endswith('requested plan')
    assert 'Do not save' in executor.run.call_args.kwargs['input_text']
    assert snapshots.capture.call_count == 2
    validator.assert_called_once_with(str(root))


@pytest.mark.parametrize('raw', [completed(''), completed('  '), 'invalid', '[]', '{}',
    completed() + '\ninvalid', completed() + '\n{}', completed() + '\n{"type":"error"}',
    completed() + '\n{"type":"turn.failed"}',
    completed() + '\n{"type":"item.completed","item":{"type":"error"}}',
    '{"type":"item.completed","item":{"type":"agent_message","text":"plan"}}'])
def test_invalid_completion_fails_without_exposing_output(runner, raw):
    plan, executor, _, snapshots, _ = runner
    executor.run.return_value = raw
    result = plan.run(AIRequest('plan'))
    assert not result.success and result.content == ''
    assert snapshots.capture.call_count == 2


def test_process_exception_still_observes_after(runner):
    plan, executor, _, snapshots, _ = runner
    executor.run.side_effect = RuntimeError('secret stderr')
    result = plan.run(AIRequest('plan'))
    assert not result.success and result.content == ''
    assert 'secret' not in result.error_message
    assert snapshots.capture.call_count == 2


@pytest.mark.parametrize('process_fails', [True, False])
def test_changes_discard_successful_body_and_report_path(runner, process_fails):
    plan, executor, root, _, _ = runner
    def execute(*args, **kwargs):
        (root / 'new-file').write_text('secret content')
        if process_fails:
            raise RuntimeError('exit 1')
        return completed()
    executor.run.side_effect = execute
    result = plan.run(AIRequest('plan'))
    assert not result.success and result.content == ''
    assert 'new-file' in result.error_message
    assert 'secret content' not in result.error_message


@pytest.mark.parametrize('phase', ['before', 'after'])
def test_observation_failure_stops(runner, phase):
    plan, executor, root, snapshots, _ = runner
    state = PlanRepositorySnapshotProvider(root).capture()
    failure = SnapshotUnavailable('Repository observation unavailable (index)')
    snapshots.capture.side_effect = [failure] if phase == 'before' else [state, failure]
    result = plan.run(AIRequest('plan'))
    assert not result.success and 'index' in result.error_message
    if phase == 'before':
        executor.run.assert_not_called()


def test_validation_required_and_failure_prevents_execution(runner):
    plan, executor, root, snapshots, validator = runner
    with pytest.raises(ValueError):
        PlanCodexRunner(executor, root, None)
    validator.side_effect = ValueError('mismatch')
    assert not plan.run(AIRequest('plan')).success
    executor.run.assert_not_called()
    snapshots.capture.assert_not_called()
