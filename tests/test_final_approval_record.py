import hashlib
import json
from dataclasses import asdict, replace
from unittest.mock import Mock

import pytest

from test_final_approval_decision import decision_target, receive
from test_final_approval_target import target_case
from test_final_approval_entry import entry_case
from test_review_handoff import handoff_case
from test_correction_continuation import continuation_case
from test_correction_routing import routing_case
from test_classify_review_result import result_case
from test_prepare_review_input import review_case


def test_explicit_final_approval_saves_and_validates_record_from_target_bytes(decision_target, tmp_path):
    from application.final_approval_record import FinalApprovalRecordInput, FinalApprovalRecordUseCase
    from infrastructure.json_approval_record_repository import JsonApprovalRecordRepository
    repository = JsonApprovalRecordRepository(tmp_path / 'approvals')
    decision = receive(decision_target, 'Final Approval')
    request = FinalApprovalRecordInput(decision, 'final-001', '2026-09-24T12:00:00+09:00', 'Human approved.')
    output = FinalApprovalRecordUseCase(repository).execute(request)
    path = decision_target.request.artifact_path
    assert output.saved and output.approval_valid and not output.failures
    assert output.approval_validation_result.is_valid
    assert output.approval_record == repository.get('final-001') == {
        'approval_id': 'final-001',
        'artifact_type': 'final_approval_target',
        'artifact_path': str(path),
        'artifact_hash': hashlib.sha256(path.read_bytes()).hexdigest(),
        'decision': 'approved',
        'approved_at': request.approved_at,
        'comment': request.comment,
    }
    assert output.approval_record['artifact_hash'] == decision_target.artifact_hash
    assert (tmp_path / 'approvals' / 'final-001.json').is_file()
    assert output.request.decision is decision


@pytest.fixture
def record_case(decision_target, tmp_path):
    from application.final_approval_record import FinalApprovalRecordInput
    from infrastructure.json_approval_record_repository import JsonApprovalRecordRepository
    request = FinalApprovalRecordInput(receive(decision_target, 'Final Approval'),
        'final-001', '2026-09-24T12:00:00+09:00', 'Human approved.')
    return request, JsonApprovalRecordRepository(tmp_path / 'approvals')


def record_approval(case):
    from application.final_approval_record import FinalApprovalRecordUseCase
    request, repository = case
    return FinalApprovalRecordUseCase(repository).execute(request)


@pytest.mark.parametrize('selection', [
    'Implementation Correction', 'Plan Revision', 'Specification Reconsideration',
    'Cancellation', None, 'pending', '', 'reject', 'rejection', 'APPROVED',
    'approved', 'CRITICAL_CHANGE_APPROVAL',
])
def test_only_explicit_final_approval_can_build_or_save_record(record_case, selection, monkeypatch):
    import application.final_approval_record as module
    request, _ = record_case
    build = Mock(side_effect=AssertionError('No record should be constructed'))
    monkeypatch.setattr(module, 'build_approval_record_from_artifact', build)
    decision = receive(request.decision.request.target, selection)
    repository = Mock()
    output = record_approval((replace(request, decision=decision), repository))
    assert not output.saved and not output.approval_valid
    assert output.approval_record is None
    assert output.approval_validation_result is None
    assert output.failures
    build.assert_not_called()
    assert repository.mock_calls == []


@pytest.mark.parametrize('kind', ['missing', 'failed', 'inconsistent', 'target_failed'])
def test_requires_consistent_successful_target_three_receipt(record_case, kind):
    from application.final_approval_decision import DecisionFailure
    from application.final_approval_target import TargetFailure
    request, _ = record_case
    decision = request.decision
    if kind == 'missing':
        decision = None
    elif kind == 'failed':
        decision = replace(decision, failures=(DecisionFailure('FAILED', 'not received'),))
    elif kind == 'inconsistent':
        decision = replace(decision, request=replace(decision.request, human_decision=None))
    else:
        target = replace(decision.request.target, failures=(TargetFailure('FAILED', 'not established'),))
        decision = replace(decision, request=replace(decision.request, target=target))
    repository = Mock()
    output = record_approval((replace(request, decision=decision), repository))
    assert not output.saved and not output.approval_valid and output.failures
    assert output.approval_record is None
    assert repository.mock_calls == []


@pytest.mark.parametrize('field', [
    'implementation_branch', 'head_commit', 'base_commit',
    'implementation_evidence_reference', 'git_diff_reference', 'review_report_reference',
    'bytes_only', 'missing',
])
def test_changed_target_cannot_receive_an_old_human_approval(record_case, field):
    request, repository = record_case
    path = request.decision.request.target.request.artifact_path
    if field == 'missing':
        path.unlink()
    elif field == 'bytes_only':
        path.write_bytes(path.read_bytes() + b'\n')
    else:
        data = json.loads(path.read_text(encoding='utf-8'))
        data[field] = 'changed-after-human-selection'
        path.write_text(json.dumps(data), encoding='utf-8')
    output = record_approval(record_case)
    assert not output.saved and not output.approval_valid
    assert output.failures and output.approval_record is None
    assert not repository.approvals_dir.exists()


@pytest.mark.parametrize('field,value', [
    ('artifact_hash', 'wrong-hash'), ('artifact_path', 'other-target.json'),
    ('decision', 'revision_requested'), ('artifact_type', 'critical_change_request'),
])
def test_validation_uses_reloaded_record_and_rejects_mismatch(record_case, monkeypatch, field, value):
    request, repository = record_case
    save = repository.save
    def save_mismatched(record):
        save({**record, field: value})
    monkeypatch.setattr(repository, 'save', save_mismatched)
    output = record_approval(record_case)
    assert output.saved and not output.approval_valid
    assert output.approval_record == repository.get(request.approval_id)
    assert output.approval_record[field] == value
    assert not output.approval_validation_result.is_valid
    assert any(f.code == 'APPROVAL_VALIDATION_FAILED' for f in output.failures)


def test_saved_metadata_mismatch_is_not_success(record_case, monkeypatch):
    _, repository = record_case
    get = repository.get
    monkeypatch.setattr(repository, 'get', lambda approval_id: {**get(approval_id), 'approval_id': 'other-approval'})
    output = record_approval(record_case)
    assert output.saved and output.approval_validation_result.is_valid
    assert not output.approval_valid
    assert [f.code for f in output.failures] == ['SAVED_RECORD_MISMATCH']


@pytest.mark.parametrize('partial', [False, True])
def test_save_failure_is_not_success_or_retried(record_case, monkeypatch, partial):
    _, repository = record_case
    save = repository.save
    def fail_save(record):
        if partial:
            save(record)
        raise OSError('save failed')
    saving = Mock(side_effect=fail_save)
    loading = Mock(side_effect=AssertionError('No validation after failed save'))
    monkeypatch.setattr(repository, 'save', saving)
    monkeypatch.setattr(repository, 'get', loading)
    output = record_approval(record_case)
    assert not output.saved and not output.approval_valid
    assert output.approval_record is not None
    assert output.approval_validation_result is None
    assert [f.code for f in output.failures] == ['APPROVAL_SAVE_FAILED']
    assert 'save failed' in output.failures[0].detail
    assert saving.call_count == 1
    loading.assert_not_called()
    assert (repository.approvals_dir / 'final-001.json').exists() is partial


def test_reload_failure_keeps_save_success_separate(record_case, monkeypatch):
    _, repository = record_case
    monkeypatch.setattr(repository, 'get', Mock(side_effect=OSError('read failed')))
    output = record_approval(record_case)
    assert output.saved and not output.approval_valid
    assert output.approval_validation_result is None
    assert [f.code for f in output.failures] == ['APPROVAL_READ_FAILED']
    assert (repository.approvals_dir / 'final-001.json').is_file()


@pytest.mark.parametrize('record', [None, {}])
def test_missing_or_malformed_saved_record_is_not_valid(record_case, monkeypatch, record):
    _, repository = record_case
    monkeypatch.setattr(repository, 'get', Mock(return_value=record))
    output = record_approval(record_case)
    assert output.saved and not output.approval_valid
    assert any(f.code == 'APPROVAL_VALIDATION_FAILED' for f in output.failures)


@pytest.mark.parametrize('exception', [False, True])
def test_validation_failure_is_not_approval_success(record_case, monkeypatch, exception):
    import application.final_approval_record as module
    from core.approval_validation import ApprovalValidationResult
    result = ApprovalValidationResult(False, 'final-001', 'final_approval_target', ['invalid'], [])
    validator = Mock(side_effect=RuntimeError('validation unavailable')) if exception else Mock(return_value=result)
    monkeypatch.setattr(module, 'validate_approval_result', validator)
    output = record_approval(record_case)
    assert output.saved and not output.approval_valid
    assert output.approval_validation_result == (None if exception else result)
    assert [f.code for f in output.failures] == ['APPROVAL_VALIDATION_FAILED']
    assert validator.call_count == 1


def test_target_change_during_save_fails_post_save_validation(record_case, monkeypatch):
    request, repository = record_case
    path = request.decision.request.target.request.artifact_path
    save = repository.save
    def change_after_save(record):
        save(record)
        path.write_bytes(path.read_bytes() + b'\n')
    monkeypatch.setattr(repository, 'save', change_after_save)
    output = record_approval(record_case)
    assert output.saved and not output.approval_valid
    assert not output.approval_validation_result.is_valid
    assert output.approval_validation_result.validation_errors == ['artifact hash does not match']


@pytest.mark.parametrize('field', ['implementation_branch', 'head_commit', 'base_commit', 'git_diff_reference'])
def test_old_saved_approval_is_invalid_after_artifact_change(record_case, field):
    from core.approval_validation import validate_approval_result
    request, repository = record_case
    output = record_approval(record_case)
    assert output.approval_valid
    path = request.decision.request.target.request.artifact_path
    record_path = repository.approvals_dir / 'final-001.json'
    record_bytes = record_path.read_bytes()
    data = json.loads(path.read_text(encoding='utf-8'))
    data[field] = 'changed-after-approval'
    path.write_text(json.dumps(data), encoding='utf-8')
    validation = validate_approval_result(repository.get(request.approval_id), str(path), 'final_approval_target')
    assert not validation.is_valid
    assert validation.validation_errors == ['artifact hash does not match']
    # An old decision cannot be reused to silently replace the saved Approval.
    repeated = record_approval(record_case)
    assert not repeated.saved and not repeated.approval_valid
    assert record_path.read_bytes() == record_bytes


@pytest.mark.parametrize('failure', [None, 'save', 'validation'])
def test_reuses_services_and_preserves_target_state_history_and_git(record_case, target_case, tmp_path, monkeypatch, failure):
    import application.final_approval_record as module
    import application.state_transition as transitions
    request, repository = record_case
    before = asdict(request)
    files = {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    build = Mock(wraps=module.build_approval_record_from_artifact)
    validate = Mock(wraps=module.validate_approval_result)
    transition = Mock(side_effect=AssertionError('No state transition in Target 4'))
    monkeypatch.setattr(module, 'build_approval_record_from_artifact', build)
    monkeypatch.setattr(module, 'validate_approval_result', validate)
    monkeypatch.setattr(transitions, 'transition_state', transition)
    if failure == 'save':
        monkeypatch.setattr(repository, 'save', Mock(side_effect=OSError('save failed')))
    elif failure == 'validation':
        validate.side_effect = RuntimeError('validation failed')
    git = target_case[5][3]
    calls = list(git.mock_calls)
    output = record_approval(record_case)
    assert output.approval_valid is (failure is None)
    assert asdict(request) == before
    assert all(p.read_bytes() == content for p, content in files.items())
    expected_files = set(files)
    if failure != 'save':
        expected_files.add(repository.approvals_dir / 'final-001.json')
        validate.assert_called_once_with(repository.get('final-001'),
            str(request.decision.request.target.request.artifact_path), 'final_approval_target')
    else:
        validate.assert_not_called()
    assert set(p for p in tmp_path.rglob('*') if p.is_file()) == expected_files
    assert build.call_count == 1
    transition.assert_not_called()
    assert git.mock_calls == calls
    target_case[5][4][3].run.assert_not_called()


def test_observed_repository_state_does_not_replace_saved_target_identity(record_case):
    request, repository = record_case
    target = request.decision.request.target
    entry = target.request.entry
    observed = replace(entry.repository_state, branch='observed-only', base_commit='c' * 40)
    changed_entry = replace(entry, repository_state=observed)
    target = replace(target, request=replace(target.request, entry=changed_entry))
    request = replace(request, decision=receive(target, 'Final Approval'))
    before = asdict(request)
    output = record_approval((request, repository))
    assert output.approval_valid
    assert output.approval_record['artifact_hash'] == target.artifact_hash
    assert target.artifact.implementation_branch != observed.branch
    assert target.artifact.base_commit != observed.base_commit
    assert asdict(request) == before
