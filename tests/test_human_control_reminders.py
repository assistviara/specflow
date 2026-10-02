"""T7 management records never authorize or execute Application work."""
from dataclasses import FrozenInstanceError, replace
import sqlite3
from types import SimpleNamespace
from uuid import uuid4

import pytest

from human_control.models import Project, Workflow, Reminder
from human_control.projects import ProjectService
from human_control.sqlite_repository import HumanControlRepository
from human_control.reminders import ReminderService
from human_control.resume import ResumeService
from test_plan_workflow import flow
from test_human_control_workflows import control
from test_human_control_resume import files


@pytest.fixture
def reminders(tmp_path):
    path = tmp_path / 'human.sqlite3'
    HumanControlRepository.initialize(path)
    repo = HumanControlRepository(path)
    p, other = Project(uuid4(), 'P'), Project(uuid4(), 'Other')
    repo.add_project(p)
    repo.add_project(other)
    w = Workflow(uuid4(), p.project_id, 'W', 'missing-spec', 'a' * 64,
                 'approval', 'state', 'history')
    foreign = replace(w, workflow_id=uuid4(), project_id=other.project_id)
    repo.add_workflow(w)
    repo.add_workflow(foreign)
    return SimpleNamespace(path=path, repo=repo, p=p, other=other, w=w,
                           foreign=foreign, service=ReminderService(repo))


def save(r, **changes):
    args = dict(project_id=r.p.project_id, text='  Human text\n保持  ', kind='要検討',
                human_confirmed=True)
    args.update(changes)
    return r.service.register(**args)


@pytest.mark.parametrize('kind', ['不具合', '改善案', '新機能候補', '将来構想', '要検討'])
@pytest.mark.parametrize('location', [None, '', '会社で確認 / 任意の場所'])
def test_register_and_reopen_preserves_record(reminders, kind, location):
    r = reminders
    result = save(r, kind=kind, location=location, workflow_id=r.w.workflow_id)
    assert result.success, result.diagnostics
    item = result.reminder
    assert item.text == '  Human text\n保持  '
    assert item.kind == kind and item.location == location
    assert item.provenance == 'human_direct'
    assert item.project_id == r.p.project_id and item.workflow_id == r.w.workflow_id
    reopened = ReminderService(HumanControlRepository(r.path))
    assert reopened.get(r.p.project_id, item.reminder_id).reminder == item
    with pytest.raises(FrozenInstanceError):
        item.reminder_id = uuid4()


@pytest.mark.parametrize('changes', [dict(kind=None), dict(kind=''), dict(kind='重要'),
    dict(kind=['不具合', '改善案']), dict(text=''), dict(text='  '), dict(text=None),
    dict(location=123), dict(project_id=None), dict(project_id=uuid4()),
    dict(workflow_id=uuid4())])
def test_invalid_input_stops_without_saving(reminders, changes):
    r = reminders
    before = r.path.read_bytes()
    result = save(r, **changes)
    assert not result.success and result.diagnostics
    assert r.path.read_bytes() == before


def test_candidate_not_saved_and_direct_origin_cannot_be_forged(reminders):
    r = reminders
    before = r.path.read_bytes()
    candidate = 'AI proposes a change'
    assert not save(r, text=candidate, human_confirmed=False).success
    assert not save(r, text=candidate, human_confirmed=1).success
    with pytest.raises(TypeError):
        save(r, provenance='ai_proposed_human_saved')
    assert r.path.read_bytes() == before
    assert r.service.list_for_project(r.p.project_id).reminders == ()
    # Representation preserves both origins; it grants no registration authority.
    item = save(r).reminder
    assert replace(item, provenance='ai_proposed_human_saved').provenance != item.provenance
    with pytest.raises(ValueError):
        replace(item, provenance='AI approved')


def test_no_implicit_workflow_and_project_lists_are_isolated(reminders):
    r = reminders
    ProjectService(r.repo).activate(r.other.project_id, human_confirmed=True)
    first = save(r).reminder
    second = save(r, project_id=r.other.project_id).reminder
    assert first.workflow_id is None and first.project_id == r.p.project_id
    assert first.reminder_id != second.reminder_id
    assert r.service.list_for_project(r.p.project_id).reminders == (first,)
    assert r.service.list_for_project(r.other.project_id).reminders == (second,)
    assert not r.service.list_for_project(uuid4()).success


def test_foreign_workflow_is_rejected(reminders):
    r = reminders
    before = r.path.read_bytes()
    assert not save(r, workflow_id=r.foreign.workflow_id).success
    assert r.path.read_bytes() == before


def test_unlink_only_changes_workflow_and_requires_human_and_owner(reminders):
    r = reminders
    item = save(r, workflow_id=r.w.workflow_id).reminder
    before = r.path.read_bytes()
    assert not r.service.unlink_workflow(r.p.project_id, item.reminder_id, human_confirmed=False).success
    assert not r.service.unlink_workflow(r.other.project_id, item.reminder_id, human_confirmed=True).success
    assert not r.service.get(r.other.project_id, item.reminder_id).success
    assert not r.service.get(r.p.project_id, uuid4()).success
    assert r.path.read_bytes() == before
    result = r.service.unlink_workflow(r.p.project_id, item.reminder_id, human_confirmed=True)
    assert result.success and result.reminder == replace(item, workflow_id=None)
    reopened = ReminderService(HumanControlRepository(r.path))
    assert reopened.list_for_project(r.p.project_id).reminders == (result.reminder,)


@pytest.mark.parametrize('operation', ['register', 'get', 'list', 'unlink'])
def test_persistence_failure_is_stop(reminders, operation):
    r = reminders
    item = save(r, workflow_id=r.w.workflow_id).reminder
    with sqlite3.connect(r.path) as db:
        db.execute('BEGIN EXCLUSIVE')
        if operation == 'register':
            result = save(r)
        elif operation == 'get':
            result = r.service.get(r.p.project_id, item.reminder_id)
        elif operation == 'list':
            result = r.service.list_for_project(r.p.project_id)
        else:
            result = r.service.unlink_workflow(r.p.project_id, item.reminder_id, human_confirmed=True)
        assert not result.success and result.diagnostics
    assert r.service.list_for_project(r.p.project_id).reminders == (item,)


def test_schema_five_rejects_real_version_four_without_changes(reminders):
    r = reminders
    with sqlite3.connect(r.path) as db:
        assert db.execute('PRAGMA user_version').fetchone()[0] == 5
        db.execute('DROP TABLE reminders')
        db.execute('PRAGMA user_version = 4')
    before = r.path.read_bytes()
    with pytest.raises(ValueError, match='no migration'):
        HumanControlRepository(r.path)
    with pytest.raises(FileExistsError):
        HumanControlRepository.initialize(r.path)
    assert r.path.read_bytes() == before


def test_repository_cannot_replace_identity_or_register_ai_origin(reminders):
    r = reminders
    item = save(r).reminder
    with pytest.raises(sqlite3.IntegrityError):
        r.repo.add_reminder(replace(item, text='Overwrite'))
    with pytest.raises(ValueError):
        r.repo.add_reminder(replace(item, reminder_id=uuid4(), provenance='ai_proposed_human_saved'))
    assert r.service.list_for_project(r.p.project_id).reminders == (item,)


@pytest.mark.parametrize('operation', ['register', 'unlink'])
def test_sql_write_failure_rolls_back_after_validation(reminders, operation):
    r = reminders
    item = save(r, workflow_id=r.w.workflow_id).reminder
    with sqlite3.connect(r.path) as db:
        event = 'INSERT' if operation == 'register' else 'UPDATE'
        db.execute(f"CREATE TRIGGER fail_write BEFORE {event} ON reminders BEGIN SELECT RAISE(ABORT, 'write failure'); END")
    result = (save(r) if operation == 'register' else r.service.unlink_workflow(
        r.p.project_id, item.reminder_id, human_confirmed=True))
    assert not result.success and result.diagnostics
    assert r.service.list_for_project(r.p.project_id).reminders == (item,)


def test_reminder_does_not_change_authority_or_execute(control, monkeypatch):
    c = control
    assert c.adapter.start(c.f.generation).success
    c.projects.activate(c.project.project_id, human_confirmed=True)
    c.repository.save_human_intent(c.project.project_id, c.work.workflow_id, 'Existing Intent')
    projection = ResumeService(c.service, c.f.repo)
    before_projection = projection.project(c.project.project_id, c.work.workflow_id,
                                            observation=c.adapter.observation())
    before = files(c.f.tmp_path)
    ports = (c.entry, c.plans, c.ports.implementation, c.ports.evidence, c.ports.review, c.ports.final)
    calls = [list(port.mock_calls) for port in ports]
    with sqlite3.connect(c.db) as db:
        tables = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name != 'reminders'")]
        rows = {table: db.execute(f'SELECT * FROM {table}').fetchall() for table in tables}
    with monkeypatch.context() as patch:
        def forbidden(*args, **kwargs):
            pytest.fail('Reminder invoked Resume')
        patch.setattr(ResumeService, 'project', forbidden)
        s = ReminderService(c.repository)
        result = s.register(c.project.project_id, 'Approve, Resume, implement and Merge now',
                            '新機能候補', workflow_id=c.work.workflow_id, human_confirmed=True)
        assert result.success
        assert s.unlink_workflow(c.project.project_id, result.reminder.reminder_id,
                                 human_confirmed=True).success
        assert s.get(c.project.project_id, result.reminder.reminder_id).success
        assert s.list_for_project(c.project.project_id).success
    assert calls == [port.mock_calls for port in ports]
    assert {k: v for k, v in before.items() if k != c.db.name} == {
        k: v for k, v in files(c.f.tmp_path).items() if k != c.db.name}
    with sqlite3.connect(c.db) as db:
        assert rows == {table: db.execute(f'SELECT * FROM {table}').fetchall() for table in tables}
    assert projection.project(c.project.project_id, c.work.workflow_id,
                              observation=c.adapter.observation()) == before_projection
