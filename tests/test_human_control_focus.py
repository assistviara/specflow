from datetime import datetime, timezone, timedelta
import sqlite3
from uuid import uuid4

import pytest

from human_control.projects import ProjectService
from human_control.sqlite_repository import HumanControlRepository
from human_control.models import Workflow


@pytest.fixture
def service(tmp_path):
    path = tmp_path / 'control.sqlite3'
    HumanControlRepository.initialize(path)
    return ProjectService(HumanControlRepository(path))


def test_creation_and_reading_do_not_activate(service):
    p = service.create('Idea')
    service.repository.get_project(p.project_id)
    service.constitution(p.project_id)
    assert service.active_project() is None
    assert p in service.sleeping_projects()
    assert service.recent_sleeping() == ()


def test_explicit_switch_reopens_with_only_one_active(service):
    a, b = service.create('A'), service.create('B')
    service.activate(a.project_id, human_confirmed=True)
    service.activate(b.project_id, human_confirmed=True)
    reopened = ProjectService(HumanControlRepository(service.repository.path))
    assert reopened.active_project() == b
    assert reopened.sleeping_projects() == (a,)
    # A switch is not an invented click on the separate Sleep action.
    assert reopened.recent_sleeping() == ()


@pytest.mark.parametrize('method', ['activate', 'sleep'])
def test_focus_requires_human_decision(service, method):
    p = service.create('Idea')
    with pytest.raises(ValueError):
        getattr(service, method)(p.project_id, human_confirmed=False)
    assert service.active_project() is None


def test_recent_sleeping_uses_last_explicit_sleep_not_updates(service):
    items = [service.create(str(i)) for i in range(5)]
    base = datetime(2026, 10, 1, tzinfo=timezone.utc)
    for i, p in enumerate(items):
        service.sleep(p.project_id, human_confirmed=True, occurred_at=base + timedelta(hours=i))
    service.repository.rename_project(items[0].project_id, 'Recently renamed')
    service.update_constitution(items[0].project_id, 'purpose', 'Recently edited')
    assert service.recent_sleeping() == tuple(reversed(items[2:]))
    service.activate(items[4].project_id, human_confirmed=True)
    assert service.recent_sleeping() == (items[3], items[2], items[1])
    service.sleep(items[1].project_id, human_confirmed=True, occurred_at=base + timedelta(hours=6))
    assert service.recent_sleeping() == (items[1], items[3], items[2])


def test_sleep_is_not_cancellation_and_preserves_all_artifacts(service, tmp_path):
    p = service.create('Idea')
    artifacts = []
    for name in ('state.json', 'history.json', 'approval.json', 'evidence.json'):
        path = tmp_path / name
        path.write_text('{"original": true}', encoding='utf-8')
        artifacts.append(path)
    w = Workflow(uuid4(), p.project_id, 'Work', 'spec.md', 'a' * 64,
                 'approval', str(artifacts[0]), str(artifacts[1]))
    service.repository.add_workflow(w)
    service.repository.set_artifact_reference(w.workflow_id, 'evidence', str(artifacts[3]))
    before = {p: p.read_bytes() for p in artifacts}
    service.activate(p.project_id, human_confirmed=True)
    service.sleep(p.project_id, human_confirmed=True)
    assert service.active_project() is None
    service.activate(p.project_id, human_confirmed=True)
    assert service.active_project() == p
    assert service.repository.get_workflow(w.workflow_id) == w
    assert {p: p.read_bytes() for p in artifacts} == before


def test_switch_failure_rolls_back_old_active(service):
    a, b = service.create('A'), service.create('B')
    service.activate(a.project_id, human_confirmed=True)
    # Fail after the transaction clears the former active project.
    with sqlite3.connect(service.repository.path) as db:
        db.execute('''CREATE TRIGGER reject_new_active BEFORE INSERT ON project_focus
            WHEN NEW.is_active = 1 BEGIN SELECT RAISE(ABORT, 'write failed'); END''')
    with pytest.raises(sqlite3.IntegrityError):
        service.activate(b.project_id, human_confirmed=True)
    assert service.active_project() == a
    assert service.sleeping_projects() == (b,)


def test_unknown_project_does_not_clear_active(service):
    p = service.create('Idea')
    service.activate(p.project_id, human_confirmed=True)
    with pytest.raises(KeyError):
        service.activate(uuid4(), human_confirmed=True)
    assert service.active_project() == p


def test_database_enforces_single_active(service):
    a, b = service.create('A'), service.create('B')
    service.activate(a.project_id, human_confirmed=True)
    with sqlite3.connect(service.repository.path) as db:
        with pytest.raises(sqlite3.IntegrityError):
            db.execute('INSERT INTO project_focus VALUES (?, 1, NULL)', (str(b.project_id),))


def test_naive_timestamp_cannot_enter_recent_history(service):
    p = service.create('Idea')
    with pytest.raises(ValueError):
        service.sleep(p.project_id, human_confirmed=True, occurred_at=datetime(2026, 10, 1))
    assert service.recent_sleeping() == ()
