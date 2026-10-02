"""T6: Human session completion is not Application workflow execution."""
from dataclasses import replace
import sqlite3
from uuid import uuid4

import pytest

from test_plan_workflow import flow
from test_human_control_workflows import control
from test_human_control_resume import files
from human_control.sqlite_repository import HumanControlRepository
from human_control.resume import ResumeService
from human_control.end_work import EndWorkService


def service(c):
    return EndWorkService(c.repository, ResumeService(c.service, c.f.repo))


def test_intent_roundtrip_update_blank_delete(control):
    c = control
    args = (c.project.project_id, c.work.workflow_id)
    assert c.repository.human_intent(*args) is None
    c.repository.save_human_intent(*args, 'Think about tests')
    reopened = HumanControlRepository(c.db)
    assert reopened.human_intent(*args) == 'Think about tests'
    reopened.save_human_intent(*args, 'New thought')
    for blank in ('', '   ', '\n\t'):
        reopened.save_human_intent(*args, blank)
        assert reopened.human_intent(*args) == 'New thought'
    s = service(c)
    assert not s.delete_intent(*args, human_confirmed=False).success
    assert reopened.human_intent(*args) == 'New thought'
    assert s.delete_intent(*args, human_confirmed=True).success
    assert reopened.human_intent(*args) is None


@pytest.mark.parametrize('operation', ['human_intent', 'save_human_intent', 'delete_human_intent'])
@pytest.mark.parametrize('wrong', ['project', 'workflow'])
def test_intent_ownership(control, operation, wrong):
    c = control
    args = [c.project.project_id, c.work.workflow_id]
    args[0 if wrong == 'project' else 1] = uuid4()
    if operation == 'save_human_intent':
        args.append('foreign')
    with pytest.raises((KeyError, ValueError)):
        getattr(c.repository, operation)(*args)


def test_intents_do_not_cross_workflows(control):
    c = control
    other = replace(c.work, workflow_id=uuid4(), name='Other')
    c.repository.add_workflow(other)
    c.repository.save_human_intent(c.project.project_id, c.work.workflow_id, 'First')
    c.repository.save_human_intent(c.project.project_id, other.workflow_id, 'Second')
    c.repository.delete_human_intent(c.project.project_id, other.workflow_id)
    assert c.repository.human_intent(c.project.project_id, c.work.workflow_id) == 'First'


def test_schema_four_and_old_database_untouched(control):
    c = control
    with sqlite3.connect(c.db) as db:
        assert db.execute('PRAGMA user_version').fetchone()[0] == 4
        db.execute('DROP TABLE human_intents')
        db.execute('PRAGMA user_version = 3')
    before = c.db.read_bytes()
    with pytest.raises(ValueError, match='no migration'):
        HumanControlRepository(c.db)
    assert c.db.read_bytes() == before


def test_end_work_after_return_preserves_formal_data_and_never_executes(control):
    c = control
    assert c.adapter.start(c.f.generation).success
    c.projects.activate(c.project.project_id, human_confirmed=True)
    observation = c.adapter.observation()
    baseline = ResumeService(c.service, c.f.repo).project(c.project.project_id,
        c.work.workflow_id, observation=observation)
    before = files(c.f.tmp_path)
    calls = (list(c.entry.mock_calls), list(c.plans.mock_calls))
    result = service(c).end(c.project.project_id, c.work.workflow_id,
        operation_returned=True, intent='Approve and Merge now', observation=observation)
    assert result.success and result.projection.reconstructed
    assert replace(result.projection, past_intent=None) == baseline
    assert result.projection.past_intent.text == 'Approve and Merge now'
    after = files(c.f.tmp_path)
    assert {k: v for k, v in after.items() if k != c.db.name} == {
        k: v for k, v in before.items() if k != c.db.name}
    assert c.projects.active_project() == c.project
    assert calls == (c.entry.mock_calls, c.plans.mock_calls)
    for port in (c.ports.implementation, c.ports.evidence, c.ports.review, c.ports.final):
        assert not port.mock_calls


def test_explicit_focus_and_sleeping_resume(control):
    c = control
    c.adapter.start(c.f.generation)
    s = service(c)
    args = (c.project.project_id, c.work.workflow_id)
    assert not s.choose_focus(*args, choice='keep_active', human_confirmed=True).success
    assert c.projects.active_project() is None
    c.projects.activate(c.project.project_id, human_confirmed=True)
    assert s.choose_focus(*args, choice='keep_active', human_confirmed=True).success
    assert not s.choose_focus(*args, choice='sleep', human_confirmed=False).success
    assert c.projects.active_project() == c.project
    assert s.end(*args, operation_returned=True, intent='Consider options').success
    before = files(c.f.tmp_path)
    assert s.choose_focus(*args, choice='sleep', human_confirmed=True).success
    assert c.projects.active_project() is None
    after = files(c.f.tmp_path)
    assert {k: v for k, v in before.items() if k != c.db.name} == {
        k: v for k, v in after.items() if k != c.db.name}
    reopened = HumanControlRepository(c.db)
    from human_control.workflows import WorkflowService
    resumed = EndWorkService(reopened, ResumeService(WorkflowService(reopened), c.f.repo)).resume(*args)
    assert resumed.success and resumed.projection.past_intent.text == 'Consider options'
    assert not resumed.projection.reconstructed  # No fabricated in-process Output.
    assert not s.choose_focus(*args, choice='keep_active', human_confirmed=True).success
    assert c.projects.active_project() is None


def test_end_requires_returned_control_and_valid_owner(control):
    c = control
    s = service(c)
    before = files(c.f.tmp_path)
    assert not s.end(c.project.project_id, c.work.workflow_id,
        operation_returned=False, intent='Do not save').success
    assert not s.end(uuid4(), c.work.workflow_id,
        operation_returned=True, intent='Do not save').success
    assert files(c.f.tmp_path) == before


@pytest.mark.parametrize('action', ['save', 'delete', 'read', 'sleep'])
def test_persistence_failure_is_safe_stop(control, action):
    c = control
    args = (c.project.project_id, c.work.workflow_id)
    c.repository.save_human_intent(*args, 'Retain')
    c.projects.activate(c.project.project_id, human_confirmed=True)
    s = service(c)
    with sqlite3.connect(c.db) as lock:
        lock.execute('BEGIN EXCLUSIVE')
        if action == 'save':
            result = s.end(*args, operation_returned=True, intent='Lost')
        elif action == 'delete':
            result = s.delete_intent(*args, human_confirmed=True)
        elif action == 'read':
            result = s.resume(*args)
        else:
            result = s.choose_focus(*args, choice='sleep', human_confirmed=True)
        assert not result.success and result.diagnostics
    assert c.repository.human_intent(*args) == 'Retain'
    assert c.projects.active_project() == c.project


def test_saved_intent_is_reported_when_following_read_fails(control, monkeypatch):
    c = control
    s = service(c)
    with monkeypatch.context() as patch:
        def fail(*args):
            raise sqlite3.OperationalError('read failed')
        patch.setattr(c.repository, 'human_intent', fail)
        result = s.end(c.project.project_id, c.work.workflow_id,
            operation_returned=True, intent='Saved before read failure')
    assert not result.success and result.intent_saved and result.diagnostics
    assert c.repository.human_intent(c.project.project_id, c.work.workflow_id) == 'Saved before read failure'


def test_sleep_write_failure_keeps_focus(control, monkeypatch):
    c = control
    c.projects.activate(c.project.project_id, human_confirmed=True)
    def fail(*args):
        raise sqlite3.OperationalError('write failed')
    monkeypatch.setattr(c.repository, 'sleep_project', fail)
    result = service(c).choose_focus(c.project.project_id, c.work.workflow_id,
        choice='sleep', human_confirmed=True)
    assert not result.success and result.diagnostics
    assert c.projects.active_project() == c.project


def test_projection_failure_preserves_facts_and_does_not_infer_from_intent(control):
    c = control
    c.adapter.start(c.f.generation)
    c.f.spec.write_text('Changed formal specification')
    result = service(c).end(c.project.project_id, c.work.workflow_id,
        operation_returned=True, intent='Everything completed', observation=c.adapter.observation())
    assert result.intent_saved
    assert not result.projection.reconstructed and not result.projection.completed
    assert result.projection.resume_point is None
    assert result.projection.history and result.diagnostics
    assert result.projection.observed_state['status'] == 'plan_approval_pending'


def test_focus_wrong_owner_and_unknown_choice_do_not_change_active(control):
    c = control
    c.projects.activate(c.project.project_id, human_confirmed=True)
    s = service(c)
    assert not s.choose_focus(uuid4(), c.work.workflow_id,
        choice='sleep', human_confirmed=True).success
    assert not s.choose_focus(c.project.project_id, c.work.workflow_id,
        choice='activate', human_confirmed=True).success
    assert c.projects.active_project() == c.project
