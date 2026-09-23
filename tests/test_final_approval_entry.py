from dataclasses import asdict, replace
import json
from unittest.mock import Mock

import pytest

from test_review_handoff import handoff_case, approved_request, prepare
from test_correction_continuation import continuation_case
from test_correction_routing import routing_case
from test_classify_review_result import result_case
from test_prepare_review_input import review_case


@pytest.fixture
def entry_case(handoff_case, tmp_path):
    handoff = prepare(approved_request(handoff_case))
    state = tmp_path / 'entry_state.json'
    state.write_text(json.dumps({'status': 'reviewing'}), encoding='utf-8')
    git = Mock()
    inp = handoff.request.continuation.request.review.review.prepared.review_input
    git.get_state.return_value = inp.repository_state
    git.get_current_head.return_value = 'b' * 40
    return handoff, state, tmp_path / 'entry_history', git, handoff_case


def test_final_approval_entry_blocks_when_current_head_is_unavailable_despite_phase_five_ready(entry_case):
    from application.final_approval_entry import FinalApprovalEntryInput, FinalApprovalEntryUseCase
    handoff, state, history, git, case = entry_case
    git.get_current_head.side_effect = OSError('HEAD unavailable')
    before = asdict(handoff)
    output = FinalApprovalEntryUseCase(git).execute(FinalApprovalEntryInput(handoff, state, history))
    assert not output.entered
    assert output.head_commit is None
    assert any(f.code == 'HEAD_ACQUISITION_FAILED' for f in output.failures)
    assert output.request.handoff is handoff
    assert output.repository_state == git.get_state.return_value
    assert json.loads(state.read_text())['status'] == 'reviewing'
    assert not history.exists()
    assert asdict(handoff) == before
    case[0]['approvals'].save.assert_not_called()
    case[3].run.assert_not_called()
    git.merge.assert_not_called()


def run_entry(case, handoff=None):
    from application.final_approval_entry import FinalApprovalEntryInput, FinalApprovalEntryUseCase
    original, state, history, git, _ = case
    return FinalApprovalEntryUseCase(git).execute(FinalApprovalEntryInput(handoff or original, state, history))


def change_review(handoff, **changes):
    from test_review_handoff import replace_review
    review = handoff.request.continuation.request.review
    return replace(handoff, request=replace_review(handoff.request, replace(review, **changes)))


def change_input(handoff, **changes):
    review = handoff.request.continuation.request.review
    prepared = review.review.prepared
    prepared = replace(prepared, review_input=replace(prepared.review_input, **changes))
    return change_review(handoff, review=replace(review.review, prepared=prepared))


def assert_blocked(case, handoff=None):
    output = run_entry(case, handoff)
    assert not output.entered
    assert output.failures
    assert json.loads(case[1].read_text())['status'] == 'reviewing'
    assert not case[2].exists()
    return output


def test_entry_transitions_only_after_validation_and_preserves_artifacts(entry_case):
    handoff, state, history, git, case = entry_case
    before = asdict(handoff)
    files = {p: p.read_bytes() for p in case[0]['request'].repository_path.rglob('*') if p.is_file()}
    output = run_entry(entry_case)
    assert output.entered and not output.failures
    assert output.head_commit == 'b' * 40
    assert output.repository_state is git.get_state.return_value
    assert json.loads(state.read_text())['status'] == 'final_approval_pending'
    records = list(history.glob('*.json'))
    assert len(records) == 1
    transition = json.loads(records[0].read_text())
    assert transition['from_state'] == 'reviewing'
    assert transition['to_state'] == 'final_approval_pending'
    assert transition['reason'] and transition['occurred_at']
    assert asdict(handoff) == before
    assert all(p.read_bytes() == content for p, content in files.items() if p != state)
    case[0]['approvals'].save.assert_not_called()
    case[3].run.assert_not_called()
    git.merge.assert_not_called()


@pytest.mark.parametrize('kind', ['NONE', 'HUMAN_REVIEW', 'CRITICAL_CHANGE_APPROVAL'])
def test_non_phase_six_handoff_is_blocked(entry_case, kind):
    assert_blocked(entry_case, replace(entry_case[0], handoff_type=kind))


@pytest.mark.parametrize('result', [None, 'REVISION_REQUIRED', 'HUMAN_REVIEW_REQUIRED'])
def test_non_approved_result_is_blocked(entry_case, result):
    assert_blocked(entry_case, change_review(entry_case[0], result=result))


@pytest.mark.parametrize('field', ['review_failures', 'validation_errors', 'execution_error', 'parse_error'])
def test_review_failure_is_not_hidden_by_ready_handoff(entry_case, field):
    value = ('failure',) if field in ('review_failures', 'validation_errors') else 'failure'
    assert_blocked(entry_case, change_review(entry_case[0], **{field: value}))


@pytest.mark.parametrize('field', ['human_questions', 'unresolved'])
def test_unresolved_review_blocks_entry(entry_case, field):
    handoff = entry_case[0]
    report = handoff.request.continuation.request.review.report
    assert_blocked(entry_case, change_review(handoff, report=replace(report, **{field: ('pending',)})))


@pytest.mark.parametrize('field', ['report', 'review_input', 'evidence', 'saved_diff', 'repository_state',
                                  'specification', 'implementation_plan', 'codex_prompt', 'test_state'])
def test_missing_required_information_blocks_entry(entry_case, field):
    handoff = entry_case[0]
    if field == 'report':
        handoff = change_review(handoff, report=None)
    elif field == 'review_input':
        review = handoff.request.continuation.request.review.review
        handoff = change_review(handoff, review=replace(review, prepared=replace(review.prepared, review_input=None)))
    else:
        handoff = change_input(handoff, **{field: None})
    assert_blocked(entry_case, handoff)


@pytest.mark.parametrize('field', ['identity', 'implementation_id', 'base_branch', 'implementation_branch', 'base_commit'])
def test_missing_saved_identity_blocks_entry(entry_case, field):
    handoff = entry_case[0]
    evidence = handoff.request.continuation.request.review.review.prepared.review_input.evidence
    identity = None if field == 'identity' else replace(evidence.identity, **{field: None if field == 'implementation_id' else ''})
    assert_blocked(entry_case, change_input(handoff, evidence=replace(evidence, identity=identity)))


def test_wrong_implementation_identity_blocks_entry(entry_case):
    from uuid import uuid4
    handoff = entry_case[0]
    assert_blocked(entry_case, replace(handoff, request=replace(handoff.request, implementation_id=uuid4())))


@pytest.mark.parametrize('field,value', [('branch', 'other'), ('base_commit', 'c' * 40),
    ('git_diff', 'unreviewed change'), ('unavailable_evidence', ('git_diff',))])
def test_observation_mismatch_preserves_saved_identity(entry_case, field, value):
    handoff, _, _, git, _ = entry_case
    before = asdict(handoff)
    git.get_state.return_value = replace(git.get_state.return_value, **{field: value})
    output = assert_blocked(entry_case)
    assert output.repository_state == git.get_state.return_value
    assert asdict(handoff) == before


@pytest.mark.parametrize('head', ['', '   ', None])
def test_missing_head_is_never_replaced_by_base(entry_case, head):
    entry_case[3].get_current_head.return_value = head
    assert_blocked(entry_case)


def test_repository_acquisition_failure_is_retained(entry_case):
    entry_case[3].get_state.side_effect = OSError('repository unavailable')
    output = assert_blocked(entry_case)
    assert any('repository unavailable' in f.detail for f in output.failures)


@pytest.mark.parametrize('part', ['state', 'history'])
def test_persistence_failure_is_not_reported_as_success(entry_case, monkeypatch, part):
    import application.state_transition as transitions
    target = 'save_current_state' if part == 'state' else 'save_state_transition_history'
    monkeypatch.setattr(transitions, target, Mock(side_effect=OSError(part + ' save failed')))
    output = run_entry(entry_case)
    assert not output.entered
    assert any(f.code == 'STATE_HISTORY_PERSISTENCE_FAILED' and part in f.detail for f in output.failures)
    expected = 'reviewing' if part == 'state' else 'final_approval_pending'
    assert json.loads(entry_case[1].read_text())['status'] == expected
    assert not entry_case[2].exists()


def test_entry_does_not_transition_from_unexpected_persisted_state(entry_case):
    entry_case[1].write_text(json.dumps({'status': 'completed'}), encoding='utf-8')
    output = run_entry(entry_case)
    assert not output.entered and output.failures
    assert json.loads(entry_case[1].read_text())['status'] == 'completed'
    assert not entry_case[2].exists()


def test_entry_retains_state_read_failure(entry_case):
    entry_case[1].unlink()
    output = run_entry(entry_case)
    assert not output.entered and output.failures
    assert not entry_case[2].exists()


def test_git_adapter_observes_head_separately_from_base(tmp_path):
    from infrastructure.git_cli_merge_service import GitCliMergeService
    from test_git_repository_state_provider import make_clean_repository, run_git
    repo, base = make_clean_repository(tmp_path)
    run_git(repo, 'checkout', '-b', 'impl/entry')
    (repo / 'tracked.txt').write_text('new implementation\n', encoding='utf-8')
    run_git(repo, 'add', 'tracked.txt')
    run_git(repo, 'commit', '-m', 'implementation')
    git = GitCliMergeService(repo)
    before = run_git(repo, 'status', '--porcelain')
    assert git.get_current_head() == run_git(repo, 'rev-parse', 'HEAD')
    assert git.get_current_head() != base
    assert git.get_state(base).base_commit == base
    assert git.get_state(base).branch == 'impl/entry'
    assert run_git(repo, 'status', '--porcelain') == before


def test_git_adapter_reports_head_failure(tmp_path):
    from infrastructure.git_cli_merge_service import GitCliMergeService
    import subprocess
    with pytest.raises(subprocess.CalledProcessError):
        GitCliMergeService(tmp_path).get_current_head()
