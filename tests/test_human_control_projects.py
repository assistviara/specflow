import sqlite3
from uuid import uuid4

import pytest

from human_control.projects import ProjectService
from human_control.models import Workflow
from human_control.sqlite_repository import HumanControlRepository


@pytest.fixture
def service(tmp_path):
    path = tmp_path / 'control.sqlite3'
    HumanControlRepository.initialize(path)
    return ProjectService(HumanControlRepository(path))


def confirm_all(service, project):
    for field in ('purpose', 'values', 'rules'):
        service.update_constitution(project.project_id, field, '現時点では特になし')
        service.confirm_constitution(project.project_id, field, '現時点では特になし', human_confirmed=True)


def test_incomplete_project_creation_is_separate_from_start_gate(service):
    p = service.create('Idea')
    assert service.repository.get_project(p.project_id) == p
    gate = service.workflow_start_gate(p.project_id)
    assert not gate.allowed
    assert set(gate.unconfirmed) == {'purpose', 'values', 'rules'}
    confirm_all(service, p)
    assert service.workflow_start_gate(p.project_id).allowed


@pytest.mark.parametrize('value', [None, '', '   '])
def test_blank_unknown_cannot_be_confirmed(service, value):
    p = service.create('Idea')
    service.update_constitution(p.project_id, 'purpose', value)
    with pytest.raises(ValueError):
        service.confirm_constitution(p.project_id, 'purpose', value, human_confirmed=True)
    assert not service.workflow_start_gate(p.project_id).allowed


def test_explicit_and_current_human_confirmation_required(service):
    p = service.create('Idea')
    service.update_constitution(p.project_id, 'purpose', 'Purpose')
    with pytest.raises(ValueError):
        service.confirm_constitution(p.project_id, 'purpose', 'Purpose', human_confirmed=False)
    with pytest.raises(ValueError):
        service.confirm_constitution(p.project_id, 'purpose', 'Old value', human_confirmed=True)
    assert not service.constitution(p.project_id)['purpose'].confirmed


def test_only_changed_item_requires_reconfirmation_and_survives_reopen(service):
    p = service.create('Idea')
    confirm_all(service, p)
    service.update_constitution(p.project_id, 'values', 'New values')
    reopened = ProjectService(HumanControlRepository(service.repository.path))
    assert reopened.workflow_start_gate(p.project_id).unconfirmed == ('values',)
    service.update_constitution(p.project_id, 'purpose', '現時点では特になし')
    assert service.constitution(p.project_id)['purpose'].confirmed


def test_change_returns_workflow_context_without_changing_formal_data(service, tmp_path):
    p = service.create('Idea')
    confirm_all(service, p)
    state = tmp_path / 'state.json'
    state.write_bytes(b'{"status":"implementing"}')
    work = Workflow(uuid4(), p.project_id, 'Work', 'spec.md', 'a' * 64,
                    'approval-1', str(state), 'history')
    service.repository.add_workflow(work)
    result = service.update_constitution(p.project_id, 'rules', 'New rules')
    assert result.human_review_required
    assert result.workflows == (work,)
    assert result.constitution['rules'].value == 'New rules'
    assert result.reason
    assert state.read_bytes() == b'{"status":"implementing"}'
    assert not service.workflow_start_gate(p.project_id).allowed


def test_existing_registration_is_explicit_and_never_imports_history(service, tmp_path):
    old = tmp_path / 'old'
    old.mkdir()
    artifact = old / 'state.json'
    artifact.write_bytes(b'{"status":"specification_editing"}')
    with pytest.raises(ValueError):
        service.register_existing('Old', str(old), human_confirmed=False)
    p = service.register_existing('Old', str(old), human_confirmed=True)
    assert service.repository.existing_project_reference(p.project_id) == str(old)
    assert service.repository.list_workflows(p.project_id) == ()
    assert not service.workflow_start_gate(p.project_id).allowed
    assert artifact.read_bytes() == b'{"status":"specification_editing"}'


def test_constitution_write_failure_preserves_confirmed_content(service):
    p = service.create('Idea')
    confirm_all(service, p)
    with sqlite3.connect(service.repository.path) as db:
        db.execute('BEGIN EXCLUSIVE')
        with pytest.raises(sqlite3.OperationalError):
            service.update_constitution(p.project_id, 'purpose', 'Not saved')
    assert service.constitution(p.project_id)['purpose'].confirmed
    assert service.constitution(p.project_id)['purpose'].value == '現時点では特になし'


def test_invalid_field_or_unknown_project_is_rejected(service):
    p = service.create('Idea')
    with pytest.raises(ValueError):
        service.update_constitution(p.project_id, 'state', 'completed')
    with pytest.raises(KeyError):
        service.workflow_start_gate(uuid4())
