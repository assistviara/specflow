from dataclasses import asdict, replace
from unittest.mock import Mock

import pytest

from test_merge_preconditions import merge_case, check
from test_final_approval_routing import approval
from test_final_approval_decision import decision_target
from test_final_approval_target import target_case
from test_final_approval_entry import entry_case
from test_review_handoff import handoff_case
from test_correction_continuation import continuation_case
from test_correction_routing import routing_case
from test_classify_review_result import result_case
from test_prepare_review_input import review_case


def test_command_success_without_verified_integration_is_not_merge_success(merge_case):
    from application.merge_execution import MergeExecutionUseCase
    from application.git_merge_service import GitMergeResult, GitMergeVerification
    ready = check(merge_case)
    assert ready.merge_ready
    _, git, approvals = merge_case
    artifact = ready.request.request.decision.request.target.artifact
    git.merge.return_value = GitMergeResult('test-repository', artifact.implementation_branch,
        'developer', artifact.head_commit, ready.observed_destination_head,
        post_commit='c' * 40, command_started=True, returncode=0)
    git.verify_merge.return_value = GitMergeVerification(integrated=False, errors=('Not integrated',))
    output = MergeExecutionUseCase(git, approvals).execute(ready)
    assert output.operation.command_success
    assert not output.verification.verified
    assert not output.succeeded
    git.merge.assert_called_once_with(artifact.implementation_branch, artifact.head_commit,
        ready.observed_destination_head)


@pytest.fixture
def execution_case(merge_case):
    from application.git_merge_service import GitMergeResult, GitMergeVerification
    ready = check(merge_case)
    assert ready.merge_ready
    _, git, approvals = merge_case
    artifact = ready.request.request.decision.request.target.artifact
    git.merge.return_value = GitMergeResult('test-repository', artifact.implementation_branch,
        'developer', artifact.head_commit, ready.observed_destination_head,
        post_commit=artifact.head_commit, command_started=True, returncode=0)
    git.verify_merge.return_value = GitMergeVerification(
        repository_state=replace(git.get_state.return_value, branch='developer'),
        current_head=artifact.head_commit, target_head=artifact.head_commit,
        source_head=artifact.head_commit, pending_operations=(), integrated=True,
        expected_tree='tree', actual_tree='tree', content_matched=True, approved_content_retained=True)
    return ready, git, approvals


def execute(case):
    from application.merge_execution import MergeExecutionUseCase
    ready, git, approvals = case
    return MergeExecutionUseCase(git, approvals).execute(ready)


@pytest.mark.parametrize('failure', [None, 'command', 'verification'])
def test_success_requires_both_steps_without_artifact_state_or_approval_writes(execution_case, tmp_path, monkeypatch, failure):
    import application.state_transition as transitions
    ready, git, approvals = execution_case
    if failure == 'command':
        git.merge.return_value = replace(git.merge.return_value, returncode=1, errors=('failed',))
    elif failure == 'verification':
        git.verify_merge.return_value = replace(git.verify_merge.return_value, errors=('verification failed',))
    before = asdict(ready)
    files = {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    transition = Mock(side_effect=AssertionError('No Target 8 transition'))
    save = Mock(side_effect=AssertionError('No Approval regeneration'))
    monkeypatch.setattr(transitions, 'transition_state', transition)
    monkeypatch.setattr(approvals, 'save', save)
    output = execute(execution_case)
    assert output.succeeded is (failure is None)
    assert output.operation is git.merge.return_value
    assert output.request is ready and output.rechecked == ready
    assert asdict(ready) == before
    assert {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()} == files
    git.merge.assert_called_once()
    assert git.verify_merge.call_count == (0 if failure == 'command' else 1)
    save.assert_not_called()
    transition.assert_not_called()


def test_target_six_failure_prevents_execution(execution_case):
    ready, git, approvals = execution_case
    output = execute((replace(ready, merge_ready=False), git, approvals))
    assert not output.succeeded and output.failures
    git.merge.assert_not_called()
    git.verify_merge.assert_not_called()


@pytest.mark.parametrize('change', ['approval', 'artifact', 'source', 'head', 'safety', 'source_missing', 'target_changed'])
def test_changed_preconditions_prevent_merge(execution_case, change):
    ready, git, approvals = execution_case
    if change == 'approval':
        record = approvals.get('final-001')
        approvals.save({**record, 'decision': 'rejected'})
    elif change == 'artifact':
        path = ready.request.request.decision.request.target.request.artifact_path
        path.write_bytes(path.read_bytes() + b'\n')
    elif change == 'source':
        git.get_state.return_value = replace(git.get_state.return_value, branch='other')
    elif change == 'head':
        git.get_current_head.return_value = 'changed'
    elif change == 'safety':
        git.get_pending_operations.return_value = ('MERGE_HEAD',)
    elif change == 'source_missing':
        git.get_branch_head.side_effect = OSError('source missing')
    else:
        original = git.get_branch_head.side_effect
        git.get_branch_head.side_effect = lambda branch: 'changed' if branch == 'developer' else original(branch)
    output = execute(execution_case)
    assert not output.succeeded and output.failures
    assert output.rechecked is not None
    git.merge.assert_not_called()


@pytest.mark.parametrize('field,value', [('returncode', 1), ('conflicts', ('file.py',)),
    ('errors', ('failure',)), ('target_branch', 'wrong'), ('approved_commit', 'changed'),
    ('pre_commit', 'changed'), ('source_branch', 'wrong')])
def test_failed_or_mismatched_operation_is_not_verified(execution_case, field, value):
    git = execution_case[1]
    git.merge.return_value = replace(git.merge.return_value, **{field: value})
    output = execute(execution_case)
    assert not output.succeeded and output.failures
    assert output.operation is git.merge.return_value
    git.merge.assert_called_once()
    git.verify_merge.assert_not_called()


@pytest.mark.parametrize('stage', ['merge', 'verify_merge'])
def test_technical_exception_is_retained_without_automatic_retry(execution_case, stage):
    git = execution_case[1]
    getattr(git, stage).side_effect = OSError('technical failure')
    output = execute(execution_case)
    assert not output.succeeded
    assert any('technical failure' in f for f in output.failures)
    assert getattr(git, stage).call_count == 1


@pytest.mark.parametrize('change', ['artifact', 'approval'])
def test_identity_changed_during_merge_is_not_success(execution_case, change):
    ready, git, approvals = execution_case
    result = git.merge.return_value
    def mutate(*args):
        if change == 'artifact':
            path = ready.request.request.decision.request.target.request.artifact_path
            path.write_bytes(path.read_bytes() + b'\n')
        else:
            record = approvals.get('final-001')
            approvals.save({**record, 'comment': 'changed'})
        return result
    git.merge.side_effect = mutate
    output = execute(execution_case)
    assert output.operation.command_success and output.verification.verified
    assert not output.succeeded and output.failures


def test_command_warnings_are_retained(execution_case):
    git = execution_case[1]
    git.merge.return_value = replace(git.merge.return_value, warnings=('Git warning',), stderr='Git warning')
    output = execute(execution_case)
    assert output.succeeded
    assert output.operation.warnings == ('Git warning',)


@pytest.mark.parametrize('field,value', [('content_matched', False),
    ('approved_content_retained', False), ('expected_tree', None), ('actual_tree', 'other')])
def test_content_verification_failure_blocks_execution_and_completion(execution_case, field, value):
    from application.phase_six_completion import PhaseSixCompletionUseCase
    ready, git, approvals = execution_case
    git.verify_merge.return_value = replace(git.verify_merge.return_value, **{field: value})
    merged = execute(execution_case)
    assert merged.operation.command_success and not merged.succeeded
    completed = PhaseSixCompletionUseCase(approvals).execute(merged)
    assert not completed.completed and completed.transition is None
    assert completed.final_state == 'final_approval_pending'
    git.verify_merge.assert_called_once_with(merged.operation,
        base_commit=ready.request.request.decision.request.target.artifact.base_commit)
