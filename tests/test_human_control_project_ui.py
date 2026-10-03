import re
from uuid import UUID, uuid4

import pytest

from app import create_app
from human_control.projects import ProjectService
from human_control.sqlite_repository import HumanControlRepository
from human_control.models import Workflow


@pytest.fixture
def ui(tmp_path):
    path = tmp_path / 'control.db'
    HumanControlRepository.initialize(path)
    app = create_app(path)
    app.testing = True
    repo = app.extensions['human_control'].require_repository()
    return app.test_client(), repo, ProjectService(repo), tmp_path


def form(client, url, action=None):
    response = client.get(url)
    assert response.status_code == 200
    text = response.get_data(as_text=True)
    forms = re.findall(r'<form.*?</form>', text, re.S)
    chosen = next(f for f in forms if action is None or f'action="{action}"' in f)
    import html
    return {key: html.unescape(value) for key, value in
            re.findall(r'<input type="hidden" name="([^"]+)" value="([^"]*)"', chosen)}


def create(client, **values):
    data = form(client, '/control/projects/new')
    data.update(name='Idea', mode='new', **values)
    return client.post('/control/projects/new', data=data), data


def test_new_get_and_index_do_not_create(ui):
    client, repo, _, _ = ui
    before = repo.path.read_bytes()
    assert client.get('/control/projects/new').status_code == 200
    assert '/control/projects/new' in client.get('/').get_data(as_text=True)
    assert repo.path.read_bytes() == before


@pytest.mark.parametrize('value,confirm,confirmed', [('', '', False), ('', 'yes', False),
    ('現時点では特になし', 'yes', True), ('入力のみ', '', False)])
def test_creation_confirmation_and_prg(ui, value, confirm, confirmed):
    client, repo, service, _ = ui
    response, data = create(client, purpose=value, confirm_purpose=confirm)
    assert response.status_code == 303
    pid = UUID(response.location.rsplit('/', 1)[-1])
    assert str(pid) != data['draft_id']
    assert service.constitution(pid)['purpose'].confirmed is confirmed
    assert not service.workflow_start_gate(pid).allowed
    assert service.active_project() is None
    assert repo.list_workflows(pid) == ()
    assert client.post('/control/projects/new', data=data).status_code == 409
    assert len(service.sleeping_projects()) == 1


@pytest.mark.parametrize('fault', ['missing', 'wrong', 'stale'])
def test_new_token_boundaries(ui, fault):
    client, repo, service, _ = ui
    data = form(client, '/control/projects/new')
    data.update(name='No create', mode='new')
    if fault == 'missing':
        data.pop('token')
    elif fault == 'wrong':
        data['draft_id'] = str(uuid4())
    else:
        client.get('/control/projects/new')
    assert client.post('/control/projects/new', data=data).status_code == 409
    assert service.sleeping_projects() == ()


@pytest.mark.parametrize('confirmed', [False, True])
def test_existing_registration_explicit(ui, confirmed):
    client, repo, service, tmp = ui
    source = tmp / 'legacy.json'
    source.write_text('{"status":"completed","approval":"fake"}')
    data = form(client, '/control/projects/new')
    data.update(name='Existing', mode='existing', reference=str(source))
    if confirmed:
        data['register_confirmed'] = 'yes'
    response = client.post('/control/projects/new', data=data)
    if not confirmed:
        assert response.status_code == 400
        assert service.sleeping_projects() == ()
    else:
        assert response.status_code == 303
        pid = UUID(response.location.rsplit('/', 1)[-1])
        assert repo.existing_project_reference(pid) == str(source)
        assert repo.list_workflows(pid) == ()
        assert service.active_project() is None
    assert source.read_text() == '{"status":"completed","approval":"fake"}'


@pytest.mark.parametrize('identity', ['name', 'bad-uuid', str(uuid4())])
def test_project_invalid_or_unknown(ui, identity):
    assert ui[0].get('/control/projects/' + identity).status_code == 404


def test_project_edit_confirm_gate_and_stale(ui):
    client, repo, service, _ = ui
    p = service.create('表示名')
    url = '/control/projects/' + str(p.project_id)
    before = repo.path.read_bytes()
    body = client.get(url).get_data(as_text=True)
    for label in ('表示名', str(p.project_id), '目的', '大切にすること', '守ること', '未確認', '開始できません', '寝かせています'):
        assert label in body
    assert repo.path.read_bytes() == before
    for field in ('purpose', 'values', 'rules'):
        action = url + '/constitution/' + field + '/edit'
        data = form(client, url, action)
        data['value'] = '現時点では特になし'
        assert client.post(action, data=data).status_code == 303
        assert not service.constitution(p.project_id)[field].confirmed
        action = url + '/constitution/' + field + '/confirm'
        data = form(client, url, action)
        data.update(human_confirmed='yes', expected_value='現時点では特になし')
        assert client.post(action, data=data).status_code == 303
    assert service.workflow_start_gate(p.project_id).allowed
    assert repo.list_workflows(p.project_id) == ()
    action = url + '/constitution/purpose/confirm'
    data = form(client, url, action)
    service.update_constitution(p.project_id, 'purpose', '変更後')
    data.update(human_confirmed='yes', expected_value='現時点では特になし')
    assert client.post(action, data=data).status_code == 409
    assert not service.constitution(p.project_id)['purpose'].confirmed
    assert service.constitution(p.project_id)['values'].confirmed
    assert service.constitution(p.project_id)['rules'].confirmed


@pytest.mark.parametrize('fault', ['missing_human', 'expected', 'wrong_target', 'missing_token'])
def test_confirmation_rejection(ui, fault):
    client, repo, service, _ = ui
    p = service.create('One')
    other = service.create('Two')
    for identity in (p.project_id, other.project_id):
        service.update_constitution(identity, 'purpose', '内容')
    url = '/control/projects/' + str(p.project_id)
    action = url + '/constitution/purpose/confirm'
    data = form(client, url, action)
    data.update(human_confirmed='yes', expected_value='内容')
    if fault == 'missing_human':
        data.pop('human_confirmed')
    elif fault == 'expected':
        data['expected_value'] = '古い内容'
    elif fault == 'wrong_target':
        action = action.replace(str(p.project_id), str(other.project_id))
    else:
        data.pop('token')
    assert client.post(action, data=data).status_code in (400, 409)
    assert not service.constitution(p.project_id)['purpose'].confirmed
    assert not service.constitution(other.project_id)['purpose'].confirmed


def test_partial_save_preserves_project_and_no_replay(ui, monkeypatch):
    client, repo, service, _ = ui
    original = ProjectService.update_constitution
    def fail(self, project_id, field, value):
        if field == 'values':
            raise OSError('secret must not appear')
        return original(self, project_id, field, value)
    monkeypatch.setattr(ProjectService, 'update_constitution', fail)
    response, data = create(client, purpose='保存済み', confirm_purpose='yes', values='失敗', rules='未処理')
    assert response.status_code == 303
    body = client.get(response.location).get_data(as_text=True)
    assert '作成済み' in body and '未保存' in body and '確認済み' in body
    assert 'secret must not appear' not in body
    pid = UUID(response.location.rsplit('/', 1)[-1])
    assert service.constitution(pid)['purpose'].confirmed
    assert not service.constitution(pid)['values'].confirmed
    assert client.post('/control/projects/new', data=data).status_code == 409
    assert len(service.sleeping_projects()) == 1


def test_change_handoff_preserves_formal_state(ui):
    client, repo, service, tmp = ui
    p = service.create('Project')
    state = tmp / 'state.json'
    state.write_text('{"status":"plan_approval_pending"}')
    work = Workflow(uuid4(), p.project_id, '現在の仕事', str(tmp / 'spec'), 'a' * 64,
        'approval', str(state), str(tmp / 'history'))
    repo.add_workflow(work)
    url = '/control/projects/' + str(p.project_id)
    action = url + '/constitution/purpose/edit'
    data = form(client, url, action)
    data['value'] = '変更'
    response = client.post(action, data=data)
    body = client.get(response.location).get_data(as_text=True)
    assert '判断が必要' in body and '現在の仕事' in body
    assert state.read_text() == '{"status":"plan_approval_pending"}'


def test_partial_confirmation_and_explicit_retry(ui, monkeypatch):
    client, repo, service, _ = ui
    def fail(*args, **kwargs):
        raise OSError('secret')
    monkeypatch.setattr(ProjectService, 'confirm_constitution', fail)
    response, data = create(client, purpose='保存された内容', confirm_purpose='yes')
    pid = UUID(response.location.rsplit('/', 1)[-1])
    body = client.get(response.location).get_data(as_text=True)
    assert '保存済みですが' in body and '確認処理に失敗' in body
    assert service.constitution(pid)['purpose'].value == '保存された内容'
    assert not service.constitution(pid)['purpose'].confirmed
    assert client.post('/control/projects/new', data=data).status_code == 409


def test_names_are_not_paths_and_html_is_escaped(ui):
    client, repo, service, tmp = ui
    data = form(client, '/control/projects/new')
    data.update(name='../<script>name</script>', mode='new')
    response = client.post('/control/projects/new', data=data)
    pid = UUID(response.location.rsplit('/', 1)[-1])
    before = set(tmp.iterdir())
    body = client.get(response.location).get_data(as_text=True)
    assert '&lt;script&gt;name&lt;/script&gt;' in body
    assert '<script>name</script>' not in body
    assert set(tmp.iterdir()) == before
    assert repo.get_project(pid).name == data['name']


def test_edit_replay_stale_and_unknown_field(ui):
    client, repo, service, _ = ui
    p = service.create('Name')
    url = '/control/projects/' + str(p.project_id)
    action = url + '/constitution/purpose/edit'
    data = form(client, url, action)
    data['value'] = 'First'
    assert client.post(action, data=data).status_code == 303
    assert client.post(action, data=data).status_code == 409
    data = form(client, url, action)
    data['value'] = 'Stale'
    service.update_constitution(p.project_id, 'purpose', 'Fresh')
    assert client.post(action, data=data).status_code == 409
    assert service.constitution(p.project_id)['purpose'].value == 'Fresh'
    assert client.post(url + '/constitution/unknown/edit', data=data).status_code == 404


@pytest.mark.parametrize('method', ['get', 'post'])
def test_target_read_failure_is_safe_stop(ui, monkeypatch, method):
    client, repo, service, _ = ui
    p = service.create('Project')
    url = '/control/projects/' + str(p.project_id)
    action = url + '/constitution/purpose/edit'
    data = form(client, url, action)
    data['value'] = 'must not save'
    before = repo.path.read_bytes()
    def fail(*args):
        raise OSError('private database diagnostic')
    monkeypatch.setattr(repo, 'get_project', fail)
    response = client.get(url) if method == 'get' else client.post(action, data=data)
    assert response.status_code == 503
    assert 'private database diagnostic' not in response.get_data(as_text=True)
    assert repo.path.read_bytes() == before
