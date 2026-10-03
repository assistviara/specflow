from datetime import datetime, timezone, timedelta
from uuid import uuid4

import pytest

from test_human_control_project_ui import ui, form
from human_control.models import Workflow


def address(project, action=None):
    url = '/control/projects/' + str(project.project_id)
    return url if action is None else url + '/focus/' + action


def focus_form(client, project, action, page=None):
    return form(client, page or address(project), address(project, action))


def test_home_empty_and_unconnected_information(ui):
    client, repo, service, _ = ui
    before = repo.path.read_bytes()
    body = client.get('/').get_data(as_text=True)
    for text in ('現在進行中のプロジェクトはありません', '最近寝かせたプロジェクトはありません',
                 'あなたの判断が必要', '未接続', '思い出しておくこと',
                 '/control/projects/sleeping', '/control/projects/new'):
        assert text in body
    assert '判断なし' not in body and '問題なし' not in body
    assert repo.path.read_bytes() == before
    assert service.active_project() is None


def test_home_active_and_sleep_order_is_service_order(ui):
    client, repo, service, _ = ui
    projects = [service.create(f'Project {n}') for n in range(5)]
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for index, p in enumerate(projects[:4]):
        service.sleep(p.project_id, human_confirmed=True, occurred_at=start + timedelta(days=index))
    service.activate(projects[4].project_id, human_confirmed=True)
    before = repo.path.read_bytes()
    body = client.get('/').get_data(as_text=True)
    assert 'Project 4' in body and '進行中（Active）' in body
    recent = body.split('id="recent-sleeping"')[1].split('</section>')[0]
    expected = service.recent_sleeping()
    assert len(expected) == 3
    assert [recent.index(p.name) for p in expected] == sorted(recent.index(p.name) for p in expected)
    assert 'Project 0' not in recent and 'Project 4' not in recent
    assert repo.path.read_bytes() == before


def test_reading_sleeping_and_project_does_not_activate(ui):
    client, repo, service, _ = ui
    p = service.create('Never active')
    before = repo.path.read_bytes()
    page = client.get('/control/projects/sleeping')
    assert page.status_code == 200 and p.name in page.get_data(as_text=True)
    assert address(p) in page.get_data(as_text=True)
    assert client.get(address(p)).status_code == 200
    assert repo.path.read_bytes() == before
    assert service.active_project() is None
    assert service.recent_sleeping() == ()


def test_activate_switch_prg_and_old_active_not_recent(ui):
    client, repo, service, _ = ui
    old, new = service.create('Previous'), service.create('Selected')
    service.activate(old.project_id, human_confirmed=True)
    data = focus_form(client, new, 'activate', '/control/projects/sleeping')
    data['human_confirmed'] = 'yes'
    response = client.post(address(new, 'activate'), data=data)
    assert response.status_code == 303
    assert service.active_project() == new
    assert old in service.sleeping_projects() and new not in service.sleeping_projects()
    assert service.recent_sleeping() == ()
    body = client.get(response.location).get_data(as_text=True)
    assert 'Previous' in body and '寝かせました' in body
    assert client.post(address(new, 'activate'), data=data).status_code == 409


def test_sleep_records_explicit_action_and_preserves_formal_data(ui):
    client, repo, service, tmp = ui
    p = service.create('Current')
    for field in ('purpose', 'values', 'rules'):
        service.update_constitution(p.project_id, field, 'Human value')
        service.confirm_constitution(p.project_id, field, 'Human value', human_confirmed=True)
    files = [tmp / name for name in ('state.json', 'approval.json', 'spec.md', 'history.json')]
    for path in files:
        path.write_text('Formal content: ' + path.name)
    repo.add_workflow(Workflow(uuid4(), p.project_id, 'Work', str(files[2]), 'a' * 64,
        'approval', str(files[0]), str(files[3])))
    before = {path: path.read_bytes() for path in files}
    service.activate(p.project_id, human_confirmed=True)
    data = focus_form(client, p, 'sleep')
    data['human_confirmed'] = 'yes'
    assert client.post(address(p, 'sleep'), data=data).status_code == 303
    assert service.active_project() is None
    assert service.recent_sleeping() == (p,)
    assert service.workflow_start_gate(p.project_id).allowed
    assert all(item.confirmed for item in service.constitution(p.project_id).values())
    assert {path: path.read_bytes() for path in files} == before
    assert client.post(address(p, 'sleep'), data=data).status_code == 409
    data = focus_form(client, p, 'activate')
    data['human_confirmed'] = 'yes'
    assert client.post(address(p, 'activate'), data=data).status_code == 303
    assert service.active_project() == p
    assert service.workflow_start_gate(p.project_id).allowed
    assert {path: path.read_bytes() for path in files} == before


@pytest.mark.parametrize('fault', ['no_token', 'bad_token', 'no_human', 'wrong_target',
    'wrong_operation', 'stale', 'deleted_target'])
def test_focus_post_rejects_invalid_context(ui, fault, monkeypatch):
    client, repo, service, _ = ui
    p, other = service.create('One'), service.create('Two')
    data = focus_form(client, p, 'activate')
    data['human_confirmed'] = 'yes'
    target = address(p, 'activate')
    if fault == 'no_token':
        data.pop('token')
    elif fault == 'bad_token':
        data['token'] = 'bad'
    elif fault == 'no_human':
        data.pop('human_confirmed')
    elif fault == 'wrong_target':
        target = address(other, 'activate')
    elif fault == 'wrong_operation':
        target = address(p, 'sleep')
    elif fault == 'stale':
        service.activate(other.project_id, human_confirmed=True)
    else:
        def missing(*args):
            raise KeyError('missing')
        monkeypatch.setattr(repo, 'get_project', missing)
    before = repo.path.read_bytes()
    assert client.post(target, data=data).status_code in (400, 404, 409)
    assert repo.path.read_bytes() == before


@pytest.mark.parametrize('identity', ['Human name', 'not-uuid', str(uuid4())])
def test_identity_not_name_and_missing_project(ui, identity):
    client, repo, service, _ = ui
    service.create('Human name')
    before = repo.path.read_bytes()
    assert client.post('/control/projects/' + identity + '/focus/activate').status_code == 404
    assert repo.path.read_bytes() == before


@pytest.mark.parametrize('action', ['sleep', 'activate'])
def test_get_cannot_change_focus(ui, action):
    client, repo, service, _ = ui
    p = service.create('Project')
    before = repo.path.read_bytes()
    assert client.get(address(p, action)).status_code == 405
    assert repo.path.read_bytes() == before


def test_sleeping_target_rejects_even_valid_token(ui):
    client, repo, service, _ = ui
    p = service.create('Already sleeping')
    app = client.application
    from human_control.focus_ui import focus_revision
    from flask import session
    with app.test_request_context('/'):
        token = app.extensions['human_control'].forms.issue('focus:sleep', p.project_id,
            revision=focus_revision(p, None))
        saved = dict(session)
    with client.session_transaction() as current:
        current.update(saved)
    before = repo.path.read_bytes()
    assert client.post(address(p, 'sleep'), data={'token': token, 'human_confirmed': 'yes'}).status_code == 409
    assert repo.path.read_bytes() == before


def test_focus_write_failure_is_not_success(ui, monkeypatch):
    client, repo, service, _ = ui
    p = service.create('Project')
    data = focus_form(client, p, 'activate')
    data['human_confirmed'] = 'yes'
    def fail(*args, **kwargs):
        raise OSError('secret diagnostic')
    monkeypatch.setattr(type(service), 'activate', fail)
    response = client.post(address(p, 'activate'), data=data)
    assert response.status_code == 503
    assert 'secret diagnostic' not in response.get_data(as_text=True)
    assert service.active_project() is None


def test_home_reminder_navigation_preserves_active_context(ui):
    client, repo, service, _ = ui
    p = service.create('Active context')
    service.activate(p.project_id, human_confirmed=True)
    body = client.get('/').get_data(as_text=True)
    assert 'このプロジェクトに関連する思い出しておくこと' in body
    assert 'すべての思い出しておくこと' in body
    assert f'href="/control/projects/{p.project_id}/reminders"' in body
    assert 'href="/control/reminders"' in body


@pytest.mark.parametrize('url', ['/', '/control/projects/sleeping'])
def test_read_failure_is_not_empty_or_success(ui, monkeypatch, url):
    client, repo, service, _ = ui
    def fail(*args):
        raise OSError('private diagnostic')
    monkeypatch.setattr(type(service), 'active_project', fail)
    response = client.get(url)
    assert response.status_code == 503
    body = response.get_data(as_text=True)
    assert 'private diagnostic' not in body
    assert '空の一覧とは判断せず' in body


def test_home_never_imports_or_displays_legacy_projects(ui, monkeypatch):
    client, repo, service, tmp = ui
    legacy = tmp / 'legacy'
    entry = legacy / 'Unregistered'
    entry.mkdir(parents=True)
    (entry / 'state.json').write_text('invalid JSON must not be read')
    monkeypatch.setattr('app.PROJECTS_DIR', legacy)
    before = repo.path.read_bytes()
    response = client.get('/')
    assert response.status_code == 200
    assert 'Unregistered' not in response.get_data(as_text=True)
    assert repo.path.read_bytes() == before
