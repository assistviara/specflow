from dataclasses import asdict, replace
import json
from unittest.mock import Mock

import pytest

from test_merge_execution import execution_case, execute
from test_merge_preconditions import merge_case
from test_final_approval_routing import approval
from test_final_approval_decision import decision_target
from test_final_approval_target import target_case
from test_final_approval_entry import entry_case
from test_review_handoff import handoff_case
from test_correction_continuation import continuation_case
from test_correction_routing import routing_case
from test_classify_review_result import result_case
from test_prepare_review_input import review_case


def test_merge_command_success_with_failed_verification_does_not_complete(execution_case):
    from application.phase_six_completion import PhaseSixCompletionUseCase
    _, git, approvals = execution_case
    git.verify_merge.return_value = replace(git.verify_merge.return_value, errors=('Not verified',))
    merged = execute(execution_case)
    assert merged.operation.command_success and not merged.succeeded
    entry = merged.request.request.request.decision.request.target.request.entry.request
    state = entry.state_file.read_bytes()
    history = {p: p.read_bytes() for p in entry.history_dir.glob('*.json')}
    output = PhaseSixCompletionUseCase(approvals).execute(merged)
    assert not output.completed and output.failures
    assert output.final_state == 'final_approval_pending'
    assert output.transition is None
    assert output.request is merged
    assert entry.state_file.read_bytes() == state
    assert {p: p.read_bytes() for p in entry.history_dir.glob('*.json')} == history


@pytest.fixture
def completion_case(execution_case):
    merged = execute(execution_case)
    assert merged.succeeded
    return merged, execution_case[1], execution_case[2]


def complete(case):
    from application.phase_six_completion import PhaseSixCompletionUseCase
    return PhaseSixCompletionUseCase(case[2]).execute(case[0])


def entry_for(merged):
    return merged.request.request.request.decision.request.target.request.entry.request


def test_completes_only_phase_six_with_history_and_lossless_handoff(completion_case, tmp_path, monkeypatch):
    import application.phase_six_completion as module
    merged, git, approvals = completion_case
    before = asdict(merged)
    files = {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    entry = entry_for(merged)
    git_calls = list(git.mock_calls)
    transition = Mock(wraps=module.transition_state)
    save = Mock(side_effect=AssertionError('Do not regenerate Approval'))
    monkeypatch.setattr(module, 'transition_state', transition)
    monkeypatch.setattr(approvals, 'save', save)
    output = complete(completion_case)
    assert output.completed and output.final_state == 'completed'
    assert not output.failures and not output.required_human_action
    assert output.request is merged
    assert output.request.request.merge_ready and output.request.rechecked.merge_ready
    assert output.request.request.request.request.decision.is_final_approval
    assert output.approval_validation.is_valid
    assert output.approval_record == approvals.get('final-001')
    assert output.request.operation.target_branch == 'developer'
    assert output.request.verification.integrated
    assert output.request.operation.post_commit == output.request.verification.target_head
    assert json.loads(entry.state_file.read_text())['status'] == 'completed'
    history_path = entry.history_dir / (output.transition['transition_id'] + '.json')
    assert json.loads(history_path.read_text()) == output.transition
    assert output.transition['from_state'] == 'final_approval_pending'
    assert output.transition['to_state'] == 'completed'
    for value in ('Phase 6', 'final-001', output.approval_record['artifact_path'],
                  output.approval_record['artifact_hash'], merged.operation.source_branch,
                  merged.operation.approved_commit, merged.operation.post_commit):
        assert value in output.transition['reason']
    transition.assert_called_once_with(entry.state_file, entry.history_dir, output.transition)
    assert asdict(merged) == before
    assert all(p.read_bytes() == data for p, data in files.items() if p != entry.state_file)
    assert set(p for p in tmp_path.rglob('*') if p.is_file()) == set(files) | {history_path}
    assert git.mock_calls == git_calls
    save.assert_not_called()


def assert_blocked(case):
    merged, git, _ = case
    entry = entry_for(merged)
    state = entry.state_file.read_bytes()
    history = {p: p.read_bytes() for p in entry.history_dir.glob('*.json')}
    calls = list(git.mock_calls)
    output = complete(case)
    assert not output.completed and output.failures and output.required_human_action
    assert output.transition is None
    assert output.request is merged
    assert entry.state_file.read_bytes() == state
    assert {p: p.read_bytes() for p in entry.history_dir.glob('*.json')} == history
    assert git.mock_calls == calls
    return output


@pytest.mark.parametrize('state', ['reviewing', 'correction_requested', 'cancelled', 'completed'])
def test_state_mismatch_does_not_transition(completion_case, state):
    entry = entry_for(completion_case[0])
    entry.state_file.write_text(json.dumps({'status': state}), encoding='utf-8')
    output = assert_blocked(completion_case)
    assert output.final_state == state


@pytest.mark.parametrize('field,value', [
    ('command_started', False), ('returncode', 1), ('conflicts', ('file.py',)),
    ('errors', ('technical failure',)), ('post_commit', None), ('post_commit', ''),
    ('source_branch', 'wrong'), ('target_branch', 'wrong'), ('approved_commit', 'wrong'),
    ('pre_commit', 'wrong'),
])
def test_merge_operation_must_satisfy_all_completion_conditions(completion_case, field, value):
    merged, git, approvals = completion_case
    changed = replace(merged, operation=replace(merged.operation, **{field: value}))
    assert_blocked((changed, git, approvals))


@pytest.mark.parametrize('field,value', [
    ('integrated', False), ('errors', ('unverified',)), ('current_head', None),
    ('target_head', 'wrong'), ('source_head', 'wrong'), ('repository_state', None),
    ('pending_operations', None), ('pending_operations', ('MERGE_HEAD',)),
])
def test_post_merge_verification_must_be_complete(completion_case, field, value):
    merged, git, approvals = completion_case
    changed = replace(merged, verification=replace(merged.verification, **{field: value}))
    assert_blocked((changed, git, approvals))


@pytest.mark.parametrize('field,value', [('branch', 'wrong'), ('git_status', '?? unapproved.py'),
    ('unavailable_evidence', ('git_status',))])
def test_post_merge_repository_failure_blocks_completion(completion_case, field, value):
    merged, git, approvals = completion_case
    state = replace(merged.verification.repository_state, **{field: value})
    assert_blocked((replace(merged, verification=replace(merged.verification, repository_state=state)), git, approvals))


@pytest.mark.parametrize('change', ['ready', 'safety', 'validation', 'recheck', 'unresolved'])
def test_preconditions_and_unresolved_failures_are_not_ignored(completion_case, change):
    merged, git, approvals = completion_case
    ready = merged.request
    if change == 'ready':
        ready = replace(ready, merge_ready=False)
    elif change == 'safety':
        ready = replace(ready, pending_operations=('rebase-merge',))
    elif change == 'validation':
        ready = replace(ready, approval_validation=replace(ready.approval_validation, is_valid=False))
    elif change == 'recheck':
        assert_blocked((replace(merged, rechecked=None), git, approvals))
        return
    else:
        assert_blocked((replace(merged, failures=('unresolved technical failure',)), git, approvals))
        return
    assert_blocked((replace(merged, request=ready, rechecked=ready), git, approvals))


@pytest.mark.parametrize('selection', [None, 'pending', 'APPROVED', 'Implementation Correction',
    'Plan Revision', 'Specification Reconsideration', 'Cancellation'])
def test_other_human_decisions_are_never_converted_to_completed(completion_case, selection):
    from test_final_approval_decision import receive
    merged, git, approvals = completion_case
    route = merged.request.request
    decision = receive(route.request.decision.request.target, selection)
    route = replace(route, request=replace(route.request, decision=decision))
    ready = replace(merged.request, request=route)
    assert_blocked((replace(merged, request=ready, rechecked=ready), git, approvals))


@pytest.mark.parametrize('change', ['missing', 'decision', 'hash', 'path'])
def test_current_saved_approval_must_remain_valid(completion_case, change):
    approvals = completion_case[2]
    if change == 'missing':
        (approvals.approvals_dir / 'final-001.json').unlink()
    else:
        record = approvals.get('final-001')
        field = {'decision': 'decision', 'hash': 'artifact_hash', 'path': 'artifact_path'}[change]
        approvals.save({**record, field: 'invalid'})
    output = assert_blocked(completion_case)
    if change != 'missing':
        assert output.approval_record is not None
        assert not output.approval_validation.is_valid


@pytest.mark.parametrize('field', ['artifact_path', 'implementation_evidence_reference',
    'git_diff_reference', 'review_report_reference'])
@pytest.mark.parametrize('change', ['missing', 'changed'])
def test_current_artifact_and_references_must_be_available_and_unchanged(completion_case, field, change):
    target = completion_case[0].request.request.request.decision.request.target
    path = getattr(target.request, field)
    if change == 'missing':
        path.unlink()
    else:
        path.write_bytes(path.read_bytes() + (b'\n' if field == 'artifact_path' else b'changed'))
    assert_blocked(completion_case)


@pytest.mark.parametrize('part', ['state', 'history'])
def test_persistence_failure_reports_observed_partial_state_without_rollback(completion_case, monkeypatch, part):
    import application.state_transition as transitions
    merged, git, _ = completion_case
    entry = entry_for(merged)
    before_history = {p: p.read_bytes() for p in entry.history_dir.glob('*.json')}
    calls = list(git.mock_calls)
    failing = Mock(side_effect=OSError(part + ' save failed'))
    monkeypatch.setattr(transitions, 'save_current_state' if part == 'state' else 'save_state_transition_history', failing)
    output = complete(completion_case)
    assert not output.completed
    assert [f.code for f in output.failures] == ['STATE_HISTORY_PERSISTENCE_FAILED']
    assert part + ' save failed' in output.failures[0].detail
    assert output.required_human_action
    expected = 'completed' if part == 'history' else 'final_approval_pending'
    assert output.final_state == expected
    assert json.loads(entry.state_file.read_text())['status'] == expected
    assert output.transition['to_state'] == 'completed'
    assert output.request is merged
    assert {p: p.read_bytes() for p in entry.history_dir.glob('*.json')} == before_history
    failing.assert_called_once()
    assert git.mock_calls == calls


def test_partial_save_and_unreadable_final_state_keep_both_failures(completion_case, monkeypatch):
    import application.state_transition as transitions
    entry = entry_for(completion_case[0])
    def failing_history(*args):
        entry.state_file.write_text('partial state data', encoding='utf-8')
        raise OSError('history failed')
    monkeypatch.setattr(transitions, 'save_state_transition_history', failing_history)
    output = complete(completion_case)
    assert not output.completed and output.final_state is None
    assert [f.code for f in output.failures] == ['STATE_HISTORY_PERSISTENCE_FAILED', 'FINAL_STATE_READ_FAILED']


def test_missing_state_is_not_reconstructed(completion_case):
    state = entry_for(completion_case[0]).state_file
    state.unlink()
    output = complete(completion_case)
    assert not output.completed and output.final_state is None
    assert output.failures[0].code == 'STATE_READ_FAILED'
    assert not state.exists()


def test_completion_does_not_rerun_readiness_merge_or_verification(completion_case, monkeypatch):
    from application.merge_preconditions import MergePreconditionsUseCase
    from application.merge_execution import MergeExecutionUseCase
    blocked = Mock(side_effect=AssertionError('Target 8 consumes existing results'))
    monkeypatch.setattr(MergePreconditionsUseCase, 'execute', blocked)
    monkeypatch.setattr(MergeExecutionUseCase, 'execute', blocked)
    git = completion_case[1]
    calls = list(git.mock_calls)
    output = complete(completion_case)
    assert output.completed
    assert git.mock_calls == calls
    blocked.assert_not_called()


def test_observed_noncompleted_state_is_retained_if_transition_did_not_persist(completion_case, monkeypatch):
    import application.phase_six_completion as module
    monkeypatch.setattr(module, 'transition_state', Mock())
    output = complete(completion_case)
    assert not output.completed and output.failures
    assert output.final_state == 'final_approval_pending'


@pytest.mark.parametrize('change', ['entry', 'review', 'unresolved', 'identity'])
def test_upstream_incompleteness_is_not_hidden_by_merge_success(completion_case, change):
    from test_merge_preconditions import with_target
    from test_final_approval_entry import change_review
    from test_final_approval_target import with_identity
    merged, git, approvals = completion_case
    target = merged.request.request.request.decision.request.target
    entry = target.request.entry
    if change == 'entry':
        entry = replace(entry, entered=False)
    elif change == 'identity':
        entry = with_identity(entry, base_commit='changed')
    else:
        handoff = entry.request.handoff
        handoff = (change_review(handoff, result='REVISION_REQUIRED') if change == 'review'
                   else replace(handoff, unresolved_issues=('Unresolved issue',)))
        entry = replace(entry, request=replace(entry.request, handoff=handoff))
    target = replace(target, request=replace(target.request, entry=entry))
    route = with_target(merged.request.request, target)
    ready = replace(merged.request, request=route)
    assert_blocked((replace(merged, request=ready, rechecked=ready), git, approvals))
