from dataclasses import replace
import pytest
from test_merge_execution import execution_case
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


def test_human_authorized_failed_operation_retries_once_and_stops_after_second_failure(execution_case, tmp_path):
    from application.technical_merge_retry import TechnicalMergeRetryUseCase, MergeRetryAuthorization
    from infrastructure.json_merge_retry_repository import JsonMergeRetryRepository
    ready, git, approvals = execution_case
    successful = git.merge.return_value
    git.merge.return_value = replace(successful, returncode=1, errors=('temporary failure',),
        post_commit=successful.pre_commit)
    git.retry_merge.return_value = git.merge.return_value
    git.get_repository_identity.return_value = successful.repository
    history = JsonMergeRetryRepository(tmp_path / 'retry-history')
    service = TechnicalMergeRetryUseCase(git, approvals, history)
    initial = service.start(ready)
    assert initial.result is not None, initial.failures
    assert not initial.result.succeeded
    git.retry_merge.assert_not_called()
    service.authorize(initial.operation_id, MergeRetryAuthorization(initial.operation_id, True, 'Safe to repeat'))
    restarted = TechnicalMergeRetryUseCase(git, approvals, history)
    retried = restarted.retry(initial.operation_id, ready)
    assert retried.retry_count == 1 and not retried.result.succeeded
    restarted_again = TechnicalMergeRetryUseCase(git, approvals, history)
    repeated = restarted_again.retry(initial.operation_id, ready)
    assert repeated.failures
    git.retry_merge.assert_called_once()



@pytest.fixture
def retry_case(execution_case, tmp_path):
    from application.technical_merge_retry import TechnicalMergeRetryUseCase, MergeRetryAuthorization
    from infrastructure.json_merge_retry_repository import JsonMergeRetryRepository
    ready, git, approvals = execution_case
    good = git.merge.return_value
    git.get_repository_identity.return_value = good.repository
    git.merge.return_value = replace(good, returncode=1, errors=('initial failure',), post_commit=good.pre_commit)
    git.retry_merge.return_value = good
    store = JsonMergeRetryRepository(tmp_path / 'retry-history')
    service = TechnicalMergeRetryUseCase(git, approvals, store)
    initial = service.start(ready)
    assert initial.result is not None, initial.failures
    auth = MergeRetryAuthorization(initial.operation_id, True, 'Human inspected the failure')
    return ready, git, approvals, store, service, initial, auth


def test_authorization_is_required_before_any_retry(retry_case):
    ready, git, _, store, service, initial, _ = retry_case
    result = service.retry(initial.operation_id, ready)
    assert result.failures and result.required_human_action
    assert store.read(initial.operation_id, 'attempt') is None
    git.retry_merge.assert_not_called()


@pytest.mark.parametrize('change', ['none', 'wrong_id', 'false', 'ambiguous', 'empty_reason', 'approved'])
def test_rejects_incomplete_or_unrelated_authorization(retry_case, change):
    ready, git, _, _, service, initial, auth = retry_case
    changes = {'none': None, 'wrong_id': replace(auth, operation_id='other'),
        'false': replace(auth, safe_reexecution_confirmed=False),
        'ambiguous': replace(auth, safe_reexecution_confirmed='yes'),
        'empty_reason': replace(auth, reason=' '), 'approved': 'Final Approval'}
    with pytest.raises(ValueError):
        service.authorize(initial.operation_id, changes[change])
    assert service.retry(initial.operation_id, ready).failures
    git.retry_merge.assert_not_called()


@pytest.mark.parametrize('change', ['artifact', 'evidence', 'diff', 'report', 'approval', 'context',
    'head', 'source', 'target', 'repository', 'branch', 'dirty', 'observed_diff', 'pending', 'unavailable'])
def test_changed_identity_or_unsafe_repository_never_consumes_retry(retry_case, change):
    ready, git, approvals, store, service, initial, auth = retry_case
    service.authorize(initial.operation_id, auth)
    target = ready.request.request.decision.request.target
    files = {'artifact': target.request.artifact_path,
        'evidence': target.request.implementation_evidence_reference,
        'diff': target.request.git_diff_reference, 'report': target.request.review_report_reference}
    if change in files:
        path = files[change]
        path.write_bytes(path.read_bytes() + b'changed')
    elif change == 'approval':
        record = approvals.get('final-001')
        approvals.save({**record, 'comment': 'changed'})
    elif change == 'context':
        ready = replace(ready, observed_destination_head='different')
    elif change == 'head':
        git.get_current_head.return_value = 'other'
    elif change in ('source', 'target'):
        original = git.get_branch_head.side_effect
        git.get_branch_head.side_effect = lambda b: 'other' if (b == 'developer') == (change == 'target') else original(b)
    elif change == 'repository':
        git.get_repository_identity.return_value = 'other repository'
    elif change == 'branch':
        git.get_state.return_value = replace(git.get_state.return_value, branch='other')
    elif change == 'dirty':
        git.get_state.return_value = replace(git.get_state.return_value, git_status='dirty')
    elif change == 'observed_diff':
        git.get_state.return_value = replace(git.get_state.return_value, git_diff='different')
    elif change == 'pending':
        git.get_pending_operations.return_value = ('MERGE_HEAD',)
    else:
        git.get_state.side_effect = OSError('unavailable')
    output = service.retry(initial.operation_id, ready)
    assert output.failures
    assert store.read(initial.operation_id, 'attempt') is None
    git.retry_merge.assert_not_called()


def test_slot_is_durable_before_git_and_exception_never_releases_it(retry_case):
    from application.technical_merge_retry import TechnicalMergeRetryUseCase
    ready, git, approvals, store, service, initial, auth = retry_case
    service.authorize(initial.operation_id, auth)
    def fail(operation):
        assert store.read(initial.operation_id, 'attempt')['slot'] == 'consumed'
        raise OSError('execution failed')
    git.retry_merge.side_effect = fail
    output = service.retry(initial.operation_id, ready)
    assert output.retry_count == 1 and not output.result.succeeded
    assert 'execution failed' in output.result.failures[0]
    assert store.read(initial.operation_id, 'result')['result']['failures']
    TechnicalMergeRetryUseCase(git, approvals, store).retry(initial.operation_id, ready)
    git.retry_merge.assert_called_once()
    assert service.start(ready).failures
    git.merge.assert_called_once()


@pytest.mark.parametrize('event', ['operation', 'initial', 'authorization', 'attempt'])
def test_missing_or_corrupted_history_is_not_unused(retry_case, event):
    ready, git, _, store, service, initial, auth = retry_case
    service.authorize(initial.operation_id, auth)
    # A partial claim is an unknown/consumed slot, never an available one.
    path = store._path(initial.operation_id, event)
    path.write_text('{', encoding='utf-8')
    outcome = service.retry(initial.operation_id, ready)
    assert outcome.failures and outcome.retry_count is None
    git.retry_merge.assert_not_called()


@pytest.mark.parametrize('event', ['operation', 'initial', 'authorization'])
def test_absent_required_history_blocks_retry(retry_case, event):
    ready, git, _, store, service, initial, auth = retry_case
    service.authorize(initial.operation_id, auth)
    store._path(initial.operation_id, event).unlink()
    assert service.retry(initial.operation_id, ready).failures
    git.retry_merge.assert_not_called()


def test_attempt_without_result_cannot_retry_after_restart(retry_case):
    from application.technical_merge_retry import TechnicalMergeRetryUseCase
    ready, git, approvals, store, service, initial, auth = retry_case
    service.authorize(initial.operation_id, auth)
    store.create(initial.operation_id, 'attempt', {'slot': 'consumed'})
    output = TechnicalMergeRetryUseCase(git, approvals, store).retry(initial.operation_id, ready)
    assert output.retry_count == 1 and output.failures
    git.retry_merge.assert_not_called()


@pytest.mark.parametrize('part', ['attempt', 'result'])
def test_persistence_failure_never_reopens_retry_slot(retry_case, monkeypatch, part):
    ready, git, _, store, service, initial, auth = retry_case
    service.authorize(initial.operation_id, auth)
    original = store.create
    def fail(op, event, value):
        if event == part:
            original(op, event, value)
            raise OSError('persist uncertain')
        original(op, event, value)
    monkeypatch.setattr(store, 'create', fail)
    output = service.retry(initial.operation_id, ready)
    assert output.failures and (output.result is None or not output.result.succeeded)
    service.retry(initial.operation_id, ready)
    assert git.retry_merge.call_count == (0 if part == 'attempt' else 1)


def test_verification_retry_after_restart_never_reexecutes_merge(execution_case, tmp_path):
    from application.technical_merge_retry import TechnicalMergeRetryUseCase, MergeRetryAuthorization
    from infrastructure.json_merge_retry_repository import JsonMergeRetryRepository
    from application.phase_six_completion import PhaseSixCompletionUseCase
    ready, git, approvals = execution_case
    good = git.verify_merge.return_value
    git.verify_merge.return_value = replace(good, content_matched=False, errors=('content unavailable',))
    git.get_repository_identity.return_value = git.merge.return_value.repository
    store = JsonMergeRetryRepository(tmp_path / 'retry-history')
    service = TechnicalMergeRetryUseCase(git, approvals, store)
    initial = service.start(ready)
    assert not initial.result.succeeded
    service.authorize(initial.operation_id, MergeRetryAuthorization(initial.operation_id, True, 'Read can be repeated'))
    git.get_state.return_value = good.repository_state
    git.get_current_head.return_value = good.current_head
    git.get_branch_head.side_effect = lambda branch: good.target_head if branch == 'developer' else good.source_head
    git.verify_merge.return_value = good
    output = TechnicalMergeRetryUseCase(git, approvals, store).retry(initial.operation_id, ready)
    assert output.result.succeeded, output.failures
    git.merge.assert_called_once()
    git.retry_merge.assert_not_called()
    assert git.verify_merge.call_count == 2
    calls = list(git.mock_calls)
    completed = PhaseSixCompletionUseCase(approvals).execute(output.result)
    assert completed.completed, completed.failures
    assert git.mock_calls == calls


@pytest.mark.parametrize('field', ['content_matched', 'approved_content_retained', 'integrated'])
def test_retry_cannot_bypass_correction_a_or_complete_failure(retry_case, field):
    from application.phase_six_completion import PhaseSixCompletionUseCase
    ready, git, approvals, _, service, initial, auth = retry_case
    service.authorize(initial.operation_id, auth)
    git.verify_merge.return_value = replace(git.verify_merge.return_value, **{field: False})
    output = service.retry(initial.operation_id, ready)
    assert not output.result.succeeded and output.required_human_action
    completed = PhaseSixCompletionUseCase(approvals).execute(output.result)
    assert not completed.completed and completed.transition is None
    assert completed.final_state == 'final_approval_pending'


def test_same_authorization_cannot_reset_retry_or_reregister_failure(retry_case):
    ready, git, _, store, service, initial, auth = retry_case
    service.authorize(initial.operation_id, auth)
    git.retry_merge.return_value = initial.result.operation
    service.retry(initial.operation_id, ready)
    with pytest.raises(ValueError):
        service.authorize(initial.operation_id, auth)
    assert service.start(ready).failures
    assert store.read(initial.operation_id, 'attempt')['retry_count'] == 1
    git.merge.assert_called_once()
    git.retry_merge.assert_called_once()


def test_repository_identity_is_recorded_with_original_failure(retry_case):
    _, _, _, store, _, initial, _ = retry_case
    record = store.read(initial.operation_id, 'operation')
    failed = store.read(initial.operation_id, 'initial')
    assert record['operation_id'] == failed['operation_id'] == initial.operation_id
    assert record['repository'] == initial.result.operation.repository
    assert failed['result']['operation']['errors'] == ['initial failure']
    assert failed['slot'] == 'available' and failed['kind'] == 'merge'


def test_merge_retry_success_keeps_history_and_can_complete(retry_case):
    from application.phase_six_completion import PhaseSixCompletionUseCase
    ready, git, approvals, store, service, initial, auth = retry_case
    service.authorize(initial.operation_id, auth)
    output = service.retry(initial.operation_id, ready)
    assert output.result.succeeded, output.failures
    history = output.result.retry_history
    assert history['initial']['result']['operation']['errors'] == ['initial failure']
    assert history['attempt']['authorization']['reason'] == auth.reason
    assert store.read(initial.operation_id, 'result')['result']['verification']['content_matched']
    calls = list(git.mock_calls)
    completed = PhaseSixCompletionUseCase(approvals).execute(output.result)
    assert completed.completed, completed.failures
    assert git.mock_calls == calls


def test_crash_after_claim_has_no_result_and_cannot_restart(retry_case):
    from application.technical_merge_retry import TechnicalMergeRetryUseCase
    ready, git, approvals, store, service, initial, auth = retry_case
    service.authorize(initial.operation_id, auth)
    git.retry_merge.side_effect = KeyboardInterrupt('simulated process termination')
    with pytest.raises(KeyboardInterrupt):
        service.retry(initial.operation_id, ready)
    assert store.read(initial.operation_id, 'attempt')['slot'] == 'consumed'
    assert store.read(initial.operation_id, 'result') is None
    output = TechnicalMergeRetryUseCase(git, approvals, store).retry(initial.operation_id, ready)
    assert output.failures
    git.retry_merge.assert_called_once()


def test_competing_process_claim_cannot_execute_twice(retry_case, monkeypatch):
    ready, git, _, store, service, initial, auth = retry_case
    service.authorize(initial.operation_id, auth)
    create = store.create
    def competing(op, event, value):
        if event == 'attempt':
            create(op, event, value)  # competing process claimed first
        create(op, event, value)
    monkeypatch.setattr(store, 'create', competing)
    output = service.retry(initial.operation_id, ready)
    assert output.failures
    git.retry_merge.assert_not_called()


@pytest.mark.parametrize('field,value', [('slot', 'unknown'), ('kind', 'correction'), ('operation_id', 'other')])
def test_unknown_slot_or_operation_kind_is_not_inferred(retry_case, field, value):
    import json
    ready, git, _, store, service, initial, auth = retry_case
    service.authorize(initial.operation_id, auth)
    record = store.read(initial.operation_id, 'initial')
    record[field] = value
    store._path(initial.operation_id, 'initial').write_text(json.dumps(record), encoding='utf-8')
    assert service.retry(initial.operation_id, ready).failures
    git.retry_merge.assert_not_called()


@pytest.mark.parametrize('event', ['registration', 'operation', 'initial'])
def test_initial_journal_failure_never_creates_retry_eligibility(execution_case, tmp_path, monkeypatch, event):
    from application.technical_merge_retry import TechnicalMergeRetryUseCase
    from infrastructure.json_merge_retry_repository import JsonMergeRetryRepository
    ready, git, approvals = execution_case
    git.get_repository_identity.return_value = git.merge.return_value.repository
    store = JsonMergeRetryRepository(tmp_path / 'history')
    original = store.create
    def fail(op, kind, value):
        if kind == event:
            raise OSError('history write failed')
        original(op, kind, value)
    monkeypatch.setattr(store, 'create', fail)
    service = TechnicalMergeRetryUseCase(git, approvals, store)
    initial = service.start(ready)
    assert initial.failures
    assert initial.result is None or not initial.result.succeeded
    assert service.retry(initial.operation_id, ready).failures
    git.retry_merge.assert_not_called()
    assert git.merge.call_count == (1 if event == 'initial' else 0)


def test_unknown_operation_is_not_assumed_unused(retry_case):
    from uuid import uuid4
    ready, git, _, _, service, _, _ = retry_case
    assert service.retry(str(uuid4()), ready).failures
    git.retry_merge.assert_not_called()


def test_retry_does_not_change_approval_artifacts_state_or_history(retry_case):
    ready, git, approvals, _, service, initial, auth = retry_case
    target = ready.request.request.decision.request.target
    entry = target.request.entry.request
    paths = [target.request.artifact_path, target.request.implementation_evidence_reference,
        target.request.git_diff_reference, target.request.review_report_reference, entry.state_file]
    before = {p: p.read_bytes() for p in paths}
    transitions = {p: p.read_bytes() for p in entry.history_dir.glob('*.json')}
    approval = approvals.get('final-001')
    service.authorize(initial.operation_id, auth)
    assert service.retry(initial.operation_id, ready).result.succeeded
    assert all(p.read_bytes() == value for p, value in before.items())
    assert {p: p.read_bytes() for p in entry.history_dir.glob('*.json')} == transitions
    assert approvals.get('final-001') == approval
