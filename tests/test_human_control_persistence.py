"""T1: identity and index persistence, never Application Layer authority."""
import sqlite3
from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from human_control.models import Project, Workflow
from human_control.sqlite_repository import HumanControlRepository
from core.approval_validation import validate_approval_result


@pytest.fixture
def repo(tmp_path):
    path = tmp_path / 'control.sqlite3'
    HumanControlRepository.initialize(path)
    return HumanControlRepository(path)


def workflow(project_id, name='Work'):
    return Workflow(uuid4(), project_id, name, 'spec.md', 'a' * 64,
                    'approval-1', 'state.json', 'state_history')


def test_rename_and_reopen_preserve_identities(repo):
    project = Project(uuid4(), 'Before')
    repo.add_project(project)
    work = workflow(project.project_id)
    repo.add_workflow(work)
    repo.rename_project(project.project_id, 'After')
    repo.rename_workflow(work.workflow_id, 'Changed')
    reopened = HumanControlRepository(repo.path)
    assert reopened.get_project(project.project_id) == Project(project.project_id, 'After')
    saved = reopened.get_workflow(work.workflow_id)
    assert saved.workflow_id == work.workflow_id
    assert saved.project_id == project.project_id
    assert saved.name == 'Changed'
    with pytest.raises(FrozenInstanceError):
        saved.workflow_id = uuid4()


def test_multiple_workflows_and_projects_remain_isolated(repo):
    p1, p2 = Project(uuid4(), 'Same name'), Project(uuid4(), 'Same name')
    repo.add_project(p1)
    repo.add_project(p2)
    a, b, c = workflow(p1.project_id), workflow(p1.project_id), workflow(p2.project_id)
    for item in (a, b, c):
        repo.add_workflow(item)
    repo.set_artifact_reference(a.workflow_id, 'evidence', 'one.json')
    repo.set_artifact_reference(b.workflow_id, 'evidence', 'two.json')
    assert {w.workflow_id for w in repo.list_workflows(p1.project_id)} == {a.workflow_id, b.workflow_id}
    assert repo.list_workflows(p2.project_id) == (c,)
    assert repo.artifact_references(a.workflow_id) == {'evidence': 'one.json'}
    assert repo.artifact_references(b.workflow_id) == {'evidence': 'two.json'}
    assert repo.artifact_references(c.workflow_id) == {}


def test_foreign_project_and_duplicate_identity_cannot_replace_records(repo):
    p = Project(uuid4(), 'Project')
    repo.add_project(p)
    w = workflow(p.project_id)
    repo.add_workflow(w)
    with pytest.raises(sqlite3.IntegrityError):
        repo.add_project(Project(p.project_id, 'Replacement'))
    with pytest.raises(sqlite3.IntegrityError):
        repo.add_workflow(workflow(uuid4()))
    with pytest.raises(sqlite3.IntegrityError):
        repo.add_workflow(w)
    assert repo.get_project(p.project_id) == p
    assert repo.list_workflows(p.project_id) == (w,)


def test_unknown_identity_is_not_silently_created(repo):
    with pytest.raises(KeyError):
        repo.get_project(uuid4())
    with pytest.raises(KeyError):
        repo.get_workflow(uuid4())
    with pytest.raises(KeyError):
        repo.rename_project(uuid4(), 'Name')
    with pytest.raises(KeyError):
        repo.rename_workflow(uuid4(), 'Name')
    with pytest.raises(sqlite3.IntegrityError):
        repo.set_artifact_reference(uuid4(), 'evidence', 'missing.json')


def test_index_does_not_create_or_modify_formal_artifacts(repo, tmp_path):
    state = tmp_path / 'state.json'
    state.write_bytes(b'{"status":"specification_ready"}')
    approval = tmp_path / 'approval.json'
    approval.write_bytes(b'{"decision":"rejected"}')
    before = state.read_bytes(), approval.read_bytes()
    p = Project(uuid4(), 'Project')
    repo.add_project(p)
    w = Workflow(uuid4(), p.project_id, 'Work', str(tmp_path / 'missing.md'),
                 'a' * 64, str(approval), str(state), str(tmp_path / 'history'))
    repo.add_workflow(w)
    repo.set_artifact_reference(w.workflow_id, 'evidence', str(tmp_path / 'missing.json'))
    repo.set_artifact_reference(w.workflow_id, 'evidence', str(tmp_path / 'changed.json'))
    assert (state.read_bytes(), approval.read_bytes()) == before
    assert not (tmp_path / 'history').exists()
    assert not (tmp_path / 'changed.json').exists()
    saved = repo.get_workflow(w.workflow_id)
    assert not validate_approval_result(None, saved.specification_path, 'specification').is_valid
    with sqlite3.connect(repo.path) as db:
        columns = {row[1] for table in ('projects', 'workflows', 'artifact_references')
                   for row in db.execute(f'PRAGMA table_info({table})')}
    assert not columns.intersection({'status', 'approved', 'approval_record', 'evidence', 'state'})


def test_write_failure_is_reported_and_existing_data_survives(repo):
    p = Project(uuid4(), 'Original')
    repo.add_project(p)
    with sqlite3.connect(repo.path) as lock:
        lock.execute('BEGIN EXCLUSIVE')
        with pytest.raises(sqlite3.OperationalError):
            repo.rename_project(p.project_id, 'Not saved')
    assert repo.get_project(p.project_id) == p


def test_initialization_never_migrates_or_overwrites_existing_files(tmp_path):
    old = tmp_path / 'legacy.json'
    old.write_bytes(b'{"status":"specification_editing"}')
    with pytest.raises(FileExistsError):
        HumanControlRepository.initialize(old)
    assert old.read_bytes() == b'{"status":"specification_editing"}'
    path = tmp_path / 'new.sqlite3'
    HumanControlRepository.initialize(path)
    with pytest.raises(FileExistsError):
        HumanControlRepository.initialize(path)
    assert old.read_bytes() == b'{"status":"specification_editing"}'


def test_open_missing_or_foreign_database_does_not_initialize_it(tmp_path):
    missing = tmp_path / 'missing.sqlite3'
    with pytest.raises((FileNotFoundError, sqlite3.OperationalError)):
        HumanControlRepository(missing)
    assert not missing.exists()
    foreign = tmp_path / 'foreign.sqlite3'
    with sqlite3.connect(foreign) as db:
        db.execute('CREATE TABLE legacy (value TEXT)')
    before = foreign.read_bytes()
    with pytest.raises(ValueError):
        HumanControlRepository(foreign)
    assert foreign.read_bytes() == before


@pytest.mark.parametrize('bad', ['not-a-uuid', None])
def test_identity_requires_uuid(bad):
    with pytest.raises(TypeError):
        Project(bad, 'Project')
    with pytest.raises(TypeError):
        workflow(bad)
