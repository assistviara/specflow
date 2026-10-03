"""T8 internal unit 4: presentation delegates continuity to T5 / T6."""
from test_human_control_project_ui import ui, form
from test_plan_workflow import flow
from test_human_control_workflows import control
from test_human_control_resume import files
from test_human_control_resume import final_projection
from test_human_control_application_adapter import connected
from app import create_app
from dataclasses import replace
from uuid import uuid4
import pytest


@pytest.fixture
def screen(control):
    c = control
    c.adapter.start(c.f.generation)
    app = create_app(c.db, approvals_dir=c.f.repo.approvals_dir)
    app.testing = True
    app.extensions['human_control'].outputs.put(c.adapter.observation())
    return c, app.test_client()


def url(c, action=None):
    base = f'/control/projects/{c.project.project_id}/workflows/{c.work.workflow_id}'
    return base + '/' + action if action else base


def post(client, c, action, page=None, **values):
    data = form(client, page or url(c), url(c, action))
    data.update(human_confirmed='yes', **values)
    return client.post(url(c, action), data=data), data


def test_project_without_workflows_offers_no_automatic_start(ui):
    client, repo, service, _ = ui
    project = service.create('Project')
    before = repo.path.read_bytes()
    response = client.get('/control/projects/' + str(project.project_id))
    assert response.status_code == 200
    assert 'まだWorkflowはありません' in response.get_data(as_text=True)
    assert repo.path.read_bytes() == before


@pytest.mark.parametrize('count', [1, 3])
def test_selection_is_explicit_and_get_never_persists(screen, count):
    c, client = screen
    works = [c.work]
    for i in range(count - 1):
        work = replace(c.work, workflow_id=uuid4(), name=f'Other {i}')
        c.repository.add_workflow(work)
        works.append(work)
    before = files(c.f.tmp_path)
    response = client.get(f'/control/projects/{c.project.project_id}')
    assert response.status_code == 200
    for work in works:
        assert str(work.workflow_id) in response.get_data(as_text=True)
    assert '確認する作業を選んでください' in response.get_data(as_text=True)
    assert files(c.f.tmp_path) == before


def test_actual_resume_output_and_intent_are_read_only(screen):
    c, client = screen
    c.repository.save_human_intent(c.project.project_id, c.work.workflow_id, 'Merge now <script>')
    before = files(c.f.tmp_path)
    calls = list(c.plans.mock_calls)
    response = client.get(url(c))
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    for text in (c.project.name, c.work.name, '前回ここまで', '計画の確認・承認を待っています',
                 '再開地点を確認できました', 'Merge now &lt;script&gt;', '実行接続は後続', 'Projectへ戻る'):
        assert text in body
    assert files(c.f.tmp_path) == before
    assert c.plans.mock_calls == calls
    assert not c.ports.final.mock_calls


@pytest.mark.parametrize('reason', ['missing', 'corrupt', 'hash mismatch', 'stale Approval',
    'ownership mismatch', 'artifact mixing', 'partial save', 'history inconsistency',
    'nonunique', 'upstream output missing'])
def test_ui_respects_every_t5_stop(screen, monkeypatch, reason):
    from human_control.resume import ResumeService, ResumeProjection
    c, client = screen
    monkeypatch.setattr(ResumeService, 'project', lambda self, p, w, **kwargs:
        ResumeProjection(p, w, diagnostics=(reason,), required_human_action=('Inspect formal inputs',)))
    body = client.get(url(c)).get_data(as_text=True)
    assert 'STOP' in body and 'Human Handoff' in body and reason in body
    assert 'Inspect formal inputs' in body
    assert '再開地点を確認できました' not in body


@pytest.mark.parametrize('damage', ['spec', 'state', 'output'])
def test_real_artifacts_and_holder_are_revalidated(screen, damage):
    c, client = screen
    assert '再開地点を確認できました' in client.get(url(c)).get_data(as_text=True)
    if damage == 'spec':
        c.f.spec.write_text('changed')
    elif damage == 'state':
        c.f.state.write_text('{')
    else:
        client.application.extensions['human_control'].outputs.clear(c.work.workflow_id)
    before = files(c.f.tmp_path)
    assert 'STOP' in client.get(url(c)).get_data(as_text=True)
    assert files(c.f.tmp_path) == before


def test_intent_update_blank_delete_never_changes_formal_artifacts(screen):
    c, client = screen
    before = files(c.f.tmp_path)
    for text in ('First thought', 'New thought', '', '   '):
        response, _ = post(client, c, 'intent', intent=text)
        assert response.status_code == 303
    assert c.repository.human_intent(c.project.project_id, c.work.workflow_id) == 'New thought'
    response, _ = post(client, c, 'delete-intent')
    assert response.status_code == 303
    assert c.repository.human_intent(c.project.project_id, c.work.workflow_id) is None
    assert {k: v for k, v in files(c.f.tmp_path).items() if k != c.db.name} == {
        k: v for k, v in before.items() if k != c.db.name}
    assert not c.ports.final.mock_calls


def test_intent_is_workflow_scoped(screen):
    c, client = screen
    other = replace(c.work, workflow_id=uuid4(), name='Other')
    c.repository.add_workflow(other)
    c.repository.save_human_intent(c.project.project_id, other.workflow_id, 'Other private thought')
    assert 'Other private thought' not in client.get(url(c)).get_data(as_text=True)
    post(client, c, 'intent', intent='This thought')
    assert c.repository.human_intent(c.project.project_id, other.workflow_id) == 'Other private thought'


@pytest.mark.parametrize('fault', ['no_token', 'wrong_token', 'wrong_operation', 'wrong_workflow',
    'stale_intent', 'stale_focus', 'stale_formal', 'no_human'])
def test_post_context_boundary(screen, fault):
    c, client = screen
    data = form(client, url(c), url(c, 'intent'))
    data.update(human_confirmed='yes', intent='Attempt', revision='forged')
    target = url(c, 'intent')
    if fault == 'no_token': data.pop('token')
    elif fault == 'wrong_token': data['token'] = 'fake'
    elif fault == 'wrong_operation': target = url(c, 'delete-intent')
    elif fault == 'wrong_workflow':
        other = replace(c.work, workflow_id=uuid4())
        c.repository.add_workflow(other)
        target = target.replace(str(c.work.workflow_id), str(other.workflow_id))
    elif fault == 'stale_intent': c.repository.save_human_intent(c.project.project_id, c.work.workflow_id, 'Changed')
    elif fault == 'stale_focus': c.projects.activate(c.project.project_id, human_confirmed=True)
    elif fault == 'stale_formal': c.f.state.write_text('{')
    else: data.pop('human_confirmed')
    before = files(c.f.tmp_path)
    assert client.post(target, data=data).status_code in (400, 409)
    assert files(c.f.tmp_path) == before


@pytest.mark.parametrize('action', ['intent', 'delete-intent', 'end-work', 'keep-active', 'sleep'])
def test_all_post_actions_reject_replay(screen, action):
    c, client = screen
    c.projects.activate(c.project.project_id, human_confirmed=True)
    page = url(c, 'end-work') if action in ('keep-active', 'sleep') else url(c)
    response, data = post(client, c, action, page, intent='Thought')
    assert response.status_code == 303
    before = files(c.f.tmp_path)
    assert client.post(url(c, action), data=data).status_code == 409
    assert files(c.f.tmp_path) == before


@pytest.mark.parametrize('identity', ['bad', 'New work', str(uuid4())])
def test_uuid_not_name(screen, identity):
    c, client = screen
    assert client.get(url(c).replace(str(c.work.workflow_id), identity)).status_code == 404


def test_cross_project_rejected(screen):
    c, client = screen
    other = c.projects.create('Other')
    target = url(c).replace(str(c.project.project_id), str(other.project_id))
    assert client.get(target).status_code == 404
    assert client.post(target + '/end-work').status_code == 404


def test_end_work_get_and_explicit_post_preserve_focus_and_formal_data(screen, monkeypatch):
    from human_control.end_work import EndWorkService
    c, client = screen
    c.projects.activate(c.project.project_id, human_confirmed=True)
    before = files(c.f.tmp_path)
    calls = []
    original = EndWorkService.end
    def end(self, *args, **kwargs):
        calls.append(kwargs)
        return original(self, *args, **kwargs)
    monkeypatch.setattr(EndWorkService, 'end', end)
    assert client.get(url(c, 'end-work')).status_code == 200
    assert not calls
    response, _ = post(client, c, 'end-work')
    assert response.status_code == 303 and response.location.endswith('/end-work')
    body = client.get(response.location).get_data(as_text=True)
    assert '今日到達した地点' in body and '計画の確認・承認を待っています' in body
    assert calls == [dict(operation_returned=True, observation=c.adapter.observation())]
    assert c.projects.active_project() == c.project
    assert files(c.f.tmp_path) == before
    assert not c.ports.final.mock_calls


def test_end_screen_intent_blank_and_explicit_focus(screen):
    c, client = screen
    c.projects.activate(c.project.project_id, human_confirmed=True)
    page = url(c, 'end-work')
    post(client, c, 'intent', page, intent='Tomorrow')
    post(client, c, 'intent', page, intent='')
    assert 'Tomorrow' in client.get(page).get_data(as_text=True)
    assert post(client, c, 'keep-active', page)[0].status_code == 303
    assert c.projects.active_project() == c.project
    assert post(client, c, 'sleep', page)[0].status_code == 303
    assert c.projects.active_project() is None
    assert c.projects.recent_sleeping() == (c.project,)
    assert '進行中にするには明示的に' in client.get(page).get_data(as_text=True)
    assert client.post(url(c, 'keep-active')).status_code == 409


def test_missing_configuration_is_stop_not_guessed(screen):
    c, _ = screen
    client = create_app(c.db).test_client()
    assert 'STOP' in client.get(url(c)).get_data(as_text=True)


def test_restart_uses_real_supported_checkpoint_without_synthesized_output(final_projection):
    x = final_projection
    c = x.c
    app = create_app(c.db, approvals_dir=c.f.repo.approvals_dir,
                     evidence_dir=c.f.tmp_path / 'evidence')
    before = files(c.f.tmp_path)
    body = app.test_client().get(url(c)).get_data(as_text=True)
    assert '最終確認・承認を待っています' in body
    assert '再開地点を確認できました' in body
    assert app.extensions['human_control'].outputs.get(c.project.project_id, c.work.workflow_id) is None
    assert files(c.f.tmp_path) == before
    x.git.merge.assert_not_called()


@pytest.mark.parametrize('action', ['keep-active', 'sleep'])
def test_sleeping_focus_even_valid_token_cannot_activate_or_resleep(screen, action):
    from flask import session
    from human_control.workflow_ui import context
    c, client = screen
    app = client.application
    with app.test_request_context('/'):
        data = context(str(c.project.project_id), str(c.work.workflow_id))
        token = data['runtime'].forms.issue('workflow:' + action, c.project.project_id,
            c.work.workflow_id, revision=data['stamp'])
        saved = dict(session)
    with client.session_transaction() as current:
        current.update(saved)
    before = files(c.f.tmp_path)
    assert client.post(url(c, action), data=dict(token=token, human_confirmed='yes')).status_code == 409
    assert files(c.f.tmp_path) == before
    assert c.projects.active_project() is None


@pytest.mark.parametrize('action', ['intent', 'delete-intent', 'end-work', 'keep-active', 'sleep'])
def test_post_failures_are_not_success(screen, monkeypatch, action):
    from human_control.end_work import EndWorkResult
    c, client = screen
    c.projects.activate(c.project.project_id, human_confirmed=True)
    service = client.application.extensions['human_continuity']
    page = url(c, 'end-work') if action in ('keep-active', 'sleep') else url(c)
    data = form(client, page, url(c, action))
    data.update(human_confirmed='yes', intent='Value')
    if action == 'intent':
        def fail(*args): raise OSError('private error')
        monkeypatch.setattr(service.repository, 'save_human_intent', fail)
    else:
        method = {'delete-intent': 'delete_intent', 'end-work': 'end'}.get(action, 'choose_focus')
        monkeypatch.setattr(service, method, lambda *args, **kwargs: EndWorkResult(False))
    response = client.post(url(c, action), data=data)
    assert response.status_code == 503
    assert 'private error' not in response.get_data(as_text=True)


def test_end_work_with_unsafe_projection_still_shows_stop(screen):
    c, client = screen
    c.f.state.write_text('{')
    response, _ = post(client, c, 'end-work')
    assert response.status_code == 303
    body = client.get(response.location).get_data(as_text=True)
    assert 'STOP' in body and '安全な現在地・再開地点を確認できません' in body
    assert '再開地点を確認できました' not in body


@pytest.mark.parametrize('action', ['intent', 'delete-intent', 'keep-active', 'sleep'])
def test_mutation_get_is_not_allowed(screen, action):
    c, client = screen
    before = files(c.f.tmp_path)
    assert client.get(url(c, action)).status_code == 405
    assert files(c.f.tmp_path) == before
