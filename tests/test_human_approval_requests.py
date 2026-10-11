from dataclasses import replace
from types import SimpleNamespace
from uuid import uuid4

import pytest

from test_plan_workflow import flow
from test_human_control_workflows import control
from test_human_control_application_adapter import connected
from application.implementation_workflow import ImplementationWorkflowOutput
from human_control.application_adapter import WorkflowObservation
from human_control.approval_requests import save_request, presentation, ROLE
from infrastructure.json_human_approval_request_repository import JsonHumanApprovalRequestRepository as Store
from app import create_app

BODY = '追加承認が必要です。\n<script>範囲の変更</script> を確認してください。'


def stopped(body=BODY):
    return ImplementationWorkflowOutput(request=None, execution=SimpleNamespace(
        implementation_id=uuid4(), implementation_result=SimpleNamespace(human_approval_required=body),
        success=False, current_state='critical_approval_pending', test_execution_record_path=None),
        stop_reason='Human Approval required.')


def test_save_reopen_workflow_display_and_escape(control):
    c = control
    p, w = c.project.project_id, c.work.workflow_id
    output = stopped()
    save_request(c.service, p, w, output)
    save_request(c.service, p, w, output)  # identical retry never overwrites
    records, error = presentation(c.service, p, w, None)
    assert not error and records[0]['body'] == BODY
    for _ in range(2):
        app = create_app(c.db, approvals_dir=c.f.repo.approvals_dir)
        page = app.test_client().get(f'/control/projects/{p}/workflows/{w}')
        assert page.status_code == 200
        assert '追加承認が必要です。' in page.get_data(as_text=True)
        assert '&lt;script&gt;' in page.get_data(as_text=True)
        assert '<script>範囲' not in page.get_data(as_text=True)


def test_repository_rejects_foreign_identity_and_collision(control):
    c = control
    p, w = c.project.project_id, c.work.workflow_id
    output = stopped()
    save_request(c.service, p, w, output)
    directory = c.service.binding(p, w)[1][ROLE]
    store = Store(directory)
    record = store.load_all(p, w)[0]
    with pytest.raises(ValueError):
        store.load_all(p, uuid4())
    with pytest.raises(ValueError):
        store.save({**record, 'body': 'different request'})
    assert store.load_all(p, w)[0] == record
    assert presentation(c.service, p, uuid4(), WorkflowObservation(p, w, (output,)))[0] == []


@pytest.mark.parametrize('failure', ['save', 'index'])
def test_failed_persistence_keeps_stop_and_memory_visible(connected, monkeypatch, failure):
    x = connected
    c = x.c
    output = stopped()
    x.implementation.execute.side_effect = lambda request: replace(output, request=request)
    assert x.adapter.start(c.f.generation).success
    if failure == 'save':
        monkeypatch.setattr(Store, 'save', lambda *args: (_ for _ in ()).throw(OSError('disk failure')))
    else:
        original = c.service.record_references
        def record(p, w, refs):
            if ROLE in refs:
                raise OSError('index failure')
            return original(p, w, refs)
        monkeypatch.setattr(c.service, 'record_references', record)
    result = x.adapter.decide_plan(c.f.decision, x.inputs)
    assert not result.success and result.waiting_for_human
    assert 'persistence failed' in result.reason
    assert 'Human Approval required' in result.reason
    assert result.outputs[-1].execution.implementation_result.human_approval_required == BODY
    x.evidence.execute.assert_not_called()
    x.git.merge.assert_not_called()
    app = create_app(c.db, approvals_dir=c.f.repo.approvals_dir)
    app.extensions['human_control'].outputs.put(x.adapter.observation())
    page = app.test_client().get(f'/control/projects/{c.project.project_id}/workflows/{c.work.workflow_id}')
    assert page.status_code == 200
    assert '追加承認が必要です。' in page.get_data(as_text=True)
    assert '永続保存を確認できません' in page.get_data(as_text=True)


def test_none_creates_no_record(control):
    c = control
    save_request(c.service, c.project.project_id, c.work.workflow_id, stopped('NONE'))
    assert ROLE not in c.repository.artifact_references(c.work.workflow_id)
