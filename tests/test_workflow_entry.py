import json
from dataclasses import replace
from unittest.mock import Mock

import pytest

import application.workflow_entry as entry
import application.state_transition as persistence

from application.workflow_entry import WorkflowEntryInput, WorkflowEntryUseCase
from core.approval_record_service import build_approval_record_from_artifact
from infrastructure.json_approval_record_repository import JsonApprovalRecordRepository


@pytest.fixture
def workflow(tmp_path):
    specification = tmp_path / 'specification.md'
    specification.write_bytes(b'# Specification\r\n')
    state_file = tmp_path / 'state.json'
    state_file.write_text(json.dumps({'status': 'specification_ready', 'repair_count': 0}))
    repository = JsonApprovalRecordRepository(tmp_path / 'approvals')
    record = build_approval_record_from_artifact(
        'spec-001', 'specification', str(specification), 'approved',
        '2026-09-26T00:00:00+09:00', 'Human approved',
    )
    repository.save(record)
    request = WorkflowEntryInput(specification, 'spec-001', state_file, tmp_path / 'history')
    return request, repository, record


def test_workflow_entry_starts_plan_generation_only_with_valid_specification_approval(workflow):
    request, repository, record = workflow
    specification, state_file = request.specification_path, request.state_file

    result = WorkflowEntryUseCase(repository).execute(request)

    assert result.can_generate_plan
    assert result.approval_validation.is_valid
    assert result.approval_record == record
    assert not result.failures
    assert json.loads(state_file.read_text()) == {'status': 'plan_generating', 'repair_count': 0}
    history = list(request.history_dir.glob('*.json'))
    assert len(history) == 1
    assert json.loads(history[0].read_text()) == result.transition
    assert result.transition['from_state'] == 'specification_ready'
    assert result.transition['to_state'] == 'plan_generating'
    assert specification.read_bytes() == b'# Specification\r\n'
    assert repository.get('spec-001') == record


def assert_stopped_without_transition(result, request):
    assert not result.can_generate_plan
    assert result.failures
    assert result.transition is None
    assert json.loads(request.state_file.read_text())['status'] == 'specification_ready'
    assert not request.history_dir.exists()


@pytest.mark.parametrize('decision', ['pending', 'reject', 'rejected', None, '', 'APPROVED'])
def test_non_approval_never_enters_workflow(workflow, decision):
    request, repository, record = workflow
    record['decision'] = decision
    repository.save(record)
    result = WorkflowEntryUseCase(repository).execute(request)
    assert_stopped_without_transition(result, request)
    assert result.approval_validation.validation_errors == ['approval decision is not approved']
    assert repository.get('spec-001') == record


@pytest.mark.parametrize(('field', 'value', 'reason'), [
    ('artifact_type', 'implementation_plan', 'artifact type does not match'),
    ('artifact_path', 'other-specification.md', 'artifact path does not match'),
    ('artifact_hash', 'stale', 'artifact hash does not match'),
])
def test_saved_approval_identity_is_not_replaced_by_observed_identity(workflow, field, value, reason):
    request, repository, record = workflow
    record[field] = value
    repository.save(record)
    result = WorkflowEntryUseCase(repository).execute(request)
    assert_stopped_without_transition(result, request)
    assert result.approval_validation.validation_errors == [reason]
    assert repository.get('spec-001') == record


def test_changed_specification_invalidates_saved_approval(workflow):
    request, repository, record = workflow
    request.specification_path.write_bytes(b'# Changed Specification\n')
    result = WorkflowEntryUseCase(repository).execute(request)
    assert_stopped_without_transition(result, request)
    assert result.approval_validation.validation_errors == ['artifact hash does not match']
    assert repository.get('spec-001') == record


@pytest.mark.parametrize(('path_kind', 'code'), [
    ('unspecified', 'SPECIFICATION_NOT_SPECIFIED'),
    ('missing', 'SPECIFICATION_NOT_FOUND'),
    ('directory', 'SPECIFICATION_IDENTITY_UNAVAILABLE'),
])
def test_specification_must_identify_an_existing_file(workflow, path_kind, code):
    request, repository, _ = workflow
    path = {'unspecified': None, 'missing': request.specification_path.with_name('absent.md'),
            'directory': request.specification_path.parent}[path_kind]
    request = replace(request, specification_path=path)
    result = WorkflowEntryUseCase(repository).execute(request)
    assert_stopped_without_transition(result, request)
    assert result.failures[0].code == code


def test_unreadable_artifact_cannot_be_approved(workflow, monkeypatch):
    request, repository, _ = workflow
    monkeypatch.setattr(type(request.specification_path), 'read_bytes', Mock(side_effect=PermissionError('denied')))
    result = WorkflowEntryUseCase(repository).execute(request)
    assert_stopped_without_transition(result, request)
    assert result.approval_validation.validation_errors == ['artifact hash could not be calculated']


def test_missing_saved_approval_does_not_create_one(workflow):
    request, repository, _ = workflow
    request = replace(request, specification_approval_id='absent')
    result = WorkflowEntryUseCase(repository).execute(request)
    assert_stopped_without_transition(result, request)
    assert result.failures[0].code == 'APPROVAL_NOT_FOUND'
    assert not (repository.approvals_dir / 'absent.json').exists()


@pytest.mark.parametrize(('mode', 'code'), [
    ('load_error', 'APPROVAL_LOAD_FAILED'),
    ('malformed', 'APPROVAL_VALIDATION_FAILED'),
    ('wrong_id', 'APPROVAL_ID_MISMATCH'),
    ('none', 'APPROVAL_INVALID'),
])
def test_approval_acquisition_and_validation_failures_stop(workflow, mode, code):
    request, _, record = workflow
    repository = Mock()
    if mode == 'load_error':
        repository.get.side_effect = OSError('unavailable')
    elif mode == 'malformed':
        repository.get.return_value = {'approval_id': 'spec-001'}
    elif mode == 'wrong_id':
        repository.get.return_value = {**record, 'approval_id': 'other'}
    else:
        repository.get.return_value = None
    result = WorkflowEntryUseCase(repository).execute(request)
    assert_stopped_without_transition(result, request)
    assert result.failures[0].code == code
    repository.save.assert_not_called()


@pytest.mark.parametrize('status', ['plan_generating', 'plan_approved', 'completed', 'cancelled', 'unknown', None])
def test_invalid_current_state_does_not_enter(workflow, status):
    request, repository, _ = workflow
    request.state_file.write_text(json.dumps({'status': status}))
    result = WorkflowEntryUseCase(repository).execute(request)
    assert not result.can_generate_plan
    assert result.failures[0].code == 'STATE_MISMATCH'
    assert result.transition is None
    assert json.loads(request.state_file.read_text()) == {'status': status}
    assert not request.history_dir.exists()


def test_state_load_failure_stops_before_transition(workflow):
    request, repository, _ = workflow
    request.state_file.write_text('invalid json')
    result = WorkflowEntryUseCase(repository).execute(request)
    assert not result.can_generate_plan
    assert result.failures[0].code == 'STATE_LOAD_FAILED'
    assert result.transition is None
    assert not request.history_dir.exists()


@pytest.mark.parametrize(('stage', 'observed_status'), [
    ('save_current_state', 'specification_ready'),
    ('save_state_transition_history', 'plan_generating'),
])
def test_persistence_failure_retains_attempt_and_actual_state(workflow, monkeypatch, stage, observed_status):
    request, repository, record = workflow
    monkeypatch.setattr(persistence, stage, Mock(side_effect=OSError(stage)))
    result = WorkflowEntryUseCase(repository).execute(request)
    assert not result.can_generate_plan
    assert result.failures[0].code == 'STATE_HISTORY_PERSISTENCE_FAILED'
    assert stage in result.failures[0].detail
    assert result.transition['to_state'] == 'plan_generating'
    assert result.current_state['status'] == observed_status
    assert json.loads(request.state_file.read_text())['status'] == observed_status
    assert not request.history_dir.exists()
    assert repository.get('spec-001') == record


def test_state_is_unknown_when_reobservation_after_failed_save_fails(workflow, monkeypatch):
    request, repository, _ = workflow
    monkeypatch.setattr(entry, 'load_current_state', Mock(side_effect=[{'status': 'specification_ready'}, OSError('unreadable')]))
    monkeypatch.setattr(entry, 'transition_state', Mock(side_effect=OSError('save failed')))
    result = WorkflowEntryUseCase(repository).execute(request)
    assert not result.can_generate_plan
    assert result.current_state is None
    assert result.transition is not None


def test_validation_exception_is_not_success(workflow, monkeypatch):
    request, repository, _ = workflow
    monkeypatch.setattr(entry, 'validate_approval_result', Mock(side_effect=ValueError('validation failed')))
    result = WorkflowEntryUseCase(repository).execute(request)
    assert_stopped_without_transition(result, request)
    assert result.failures[0].code == 'APPROVAL_VALIDATION_FAILED'
