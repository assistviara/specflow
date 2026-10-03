"""T8 internal unit 5: Human direct Reminder UI boundaries."""
from test_human_control_project_ui import ui, form
from dataclasses import replace
from uuid import uuid4
from types import SimpleNamespace
import pytest
from werkzeug.datastructures import MultiDict
from human_control.models import Workflow, REMINDER_KINDS
from human_control.reminders import ReminderService, ReminderResult


@pytest.fixture
def view(ui):
    client, repo, projects, tmp = ui
    p, other = projects.create('One'), projects.create('Other')
    work = Workflow(uuid4(), p.project_id, 'Work', str(tmp / 'spec.md'), 'a' * 64,
                    'approval', str(tmp / 'state.json'), str(tmp / 'history'))
    foreign = replace(work, workflow_id=uuid4(), project_id=other.project_id, name='Foreign')
    repo.add_workflow(work)
    repo.add_workflow(foreign)
    return SimpleNamespace(**locals(), service=ReminderService(repo))


def listing(v, project=None):
    return f'/control/projects/{(project or v.p).project_id}/reminders'


def create(v, **values):
    target = listing(v) + '/new'
    data = form(v.client, target)
    data.update(kind='要検討', text='Human text', human_confirmed='yes', **values)
    return v.client.post(target, data=data), data


def saved(v, **values):
    args = dict(project_id=v.p.project_id, text='Saved thought', kind='改善案', human_confirmed=True)
    args.update(values)
    result = v.service.register(**args)
    assert result.success
    return result.reminder


def detach(v, item):
    return listing(v) + f'/{item.reminder_id}/detach'


def test_all_reminders_get_is_read_only(ui):
    client, repo, projects, _ = ui
    projects.create('Project')
    before = repo.path.read_bytes()
    response = client.get('/control/reminders')
    assert response.status_code == 200
    assert '思い出しておくこと' in response.get_data(as_text=True)
    assert repo.path.read_bytes() == before


def test_lists_display_context_without_cross_project_or_workflow_mixing(view):
    v = view
    saved(v, workflow_id=v.work.workflow_id, text='<script>Context</script>', location='任意の場所')
    saved(v, text='Unlinked')
    saved(v, project_id=v.other.project_id, text='Foreign thought')
    before = v.repo.path.read_bytes()
    all_body = v.client.get('/control/reminders').get_data(as_text=True)
    for text in ('One', 'Other', '改善案', '&lt;script&gt;Context&lt;/script&gt;', '任意の場所',
                 'Work', 'Humanが直接残したもの', 'Foreign thought', 'Unlinked'):
        assert text in all_body
    body = v.client.get(listing(v)).get_data(as_text=True)
    assert 'Foreign thought' not in body
    body = v.client.get(listing(v) + '?workflow_id=' + str(v.work.workflow_id)).get_data(as_text=True)
    assert 'Context' in body and 'Unlinked' not in body and 'Foreign thought' not in body
    assert v.repo.path.read_bytes() == before


def test_home_links_active_only_and_never_substitutes_sleeping(view):
    v = view
    saved(v, text='Sleeping secret')
    before = v.repo.path.read_bytes()
    body = v.client.get('/').get_data(as_text=True)
    assert 'href="/control/reminders"' in body
    assert 'Sleeping secret' not in body and f'href="{listing(v)}"' not in body
    assert v.repo.path.read_bytes() == before
    v.projects.activate(v.p.project_id, human_confirmed=True)
    before = v.repo.path.read_bytes()
    body = v.client.get('/').get_data(as_text=True)
    assert f'href="{listing(v)}"' in body
    assert 'Sleeping secret' not in body
    assert v.repo.path.read_bytes() == before


def test_project_and_workflow_links_preserve_existing_content(view):
    v = view
    before = v.repo.path.read_bytes()
    body = v.client.get(f'/control/projects/{v.p.project_id}').get_data(as_text=True)
    for text in ('Workflow Start Gate', 'Work', 'Sleeping', listing(v)):
        assert text in body
    body = v.client.get(f'/control/projects/{v.p.project_id}/workflows/{v.work.workflow_id}').get_data(as_text=True)
    assert listing(v) + '?workflow_id=' + str(v.work.workflow_id) in body
    assert listing(v) + '/new?workflow_id=' + str(v.work.workflow_id) in body
    assert '前回ここまで' in body and 'Human Intent' in body
    assert v.repo.path.read_bytes() == before


@pytest.mark.parametrize('kind', REMINDER_KINDS)
def test_human_direct_create_prg_replay_and_no_formal_change(view, kind):
    v = view
    files = [v.tmp / name for name in ('state.json', 'approval.json', 'evidence.json', 'review.json', 'final.json')]
    for path in files: path.write_text('Formal bytes')
    before = {p: p.read_bytes() for p in files}
    target = listing(v) + '/new'
    data = form(v.client, target)
    data.update(kind=kind, text='  Text\n保持  ', location='自由な場所', human_confirmed='yes',
                provenance='ai_proposed_human_saved', priority='high', project_id=str(v.other.project_id))
    response = v.client.post(target, data=data)
    assert response.status_code == 303 and response.location == listing(v)
    item, = v.repo.list_reminders(v.p.project_id)
    assert item.kind == kind and item.text == '  Text\n保持  ' and item.location == '自由な場所'
    assert item.workflow_id is None and item.provenance == 'human_direct'
    assert not v.repo.list_reminders(v.other.project_id)
    assert not hasattr(item, 'priority')
    assert v.client.post(target, data=data).status_code == 409
    assert {p: p.read_bytes() for p in files} == before
    assert v.projects.active_project() is None


def test_workflow_context_is_unselected_candidate_and_needs_confirmation(view):
    v = view
    target = listing(v) + '/new'
    page = target + '?workflow_id=' + str(v.work.workflow_id)
    before = v.repo.path.read_bytes()
    body = v.client.get(page).get_data(as_text=True)
    assert '関連付け候補' in body and 'Work' in body
    assert f'value="{v.work.workflow_id}" selected' not in body
    assert v.repo.path.read_bytes() == before
    data = form(v.client, page)
    data.update(kind='不具合', text='Issue', human_confirmed='yes', workflow_id=str(v.work.workflow_id))
    assert v.client.post(target, data=data).status_code == 400
    assert not v.repo.list_reminders(v.p.project_id)
    data = form(v.client, page)
    data.update(kind='不具合', text='Issue', human_confirmed='yes', workflow_id=str(v.work.workflow_id),
                confirm_workflow='yes')
    assert v.client.post(target, data=data).status_code == 303
    assert v.repo.list_reminders(v.p.project_id)[0].workflow_id == v.work.workflow_id


@pytest.mark.parametrize('fault', ['kind_missing', 'kind_unknown', 'kind_multiple', 'blank', 'no_human',
    'no_token', 'bad_token', 'foreign_workflow', 'missing_workflow', 'workflow_name',
    'wrong_project', 'stale_project', 'stale_workflow'])
def test_create_rejects_invalid_or_stale_context(view, fault):
    v = view
    target = listing(v) + '/new'
    data = MultiDict(form(v.client, target))
    data.update(dict(kind='要検討', text='Attempt', human_confirmed='yes', confirm_workflow='yes'))
    if fault == 'kind_missing': data.pop('kind')
    elif fault == 'kind_unknown': data['kind'] = '未分類'
    elif fault == 'kind_multiple': data.add('kind', '不具合')
    elif fault == 'blank': data['text'] = '   '
    elif fault == 'no_human': data.pop('human_confirmed')
    elif fault == 'no_token': data.pop('token')
    elif fault == 'bad_token': data['token'] = 'bad'
    elif fault == 'foreign_workflow': data['workflow_id'] = str(v.foreign.workflow_id)
    elif fault == 'missing_workflow': data['workflow_id'] = str(uuid4())
    elif fault == 'workflow_name': data['workflow_id'] = v.work.name
    elif fault == 'wrong_project': target = listing(v, v.other) + '/new'
    elif fault == 'stale_project': v.repo.rename_project(v.p.project_id, 'Changed')
    else: v.repo.add_workflow(replace(v.work, workflow_id=uuid4(), name='New option'))
    before = v.repo.path.read_bytes()
    assert v.client.post(target, data=data).status_code in (400, 404, 409)
    assert v.repo.path.read_bytes() == before


@pytest.mark.parametrize('identity', ['One', 'not-uuid', str(uuid4())])
def test_project_uuid_required(view, identity):
    v = view
    path = f'/control/projects/{identity}/reminders'
    assert v.client.get(path).status_code == 404
    assert v.client.post(path + '/new').status_code == 404


def test_foreign_workflow_filter_and_candidate_rejected(view):
    v = view
    for path in (listing(v), listing(v) + '/new'):
        assert v.client.get(path + '?workflow_id=' + str(v.foreign.workflow_id)).status_code == 404


def test_detach_preserves_record_provenance_and_requires_post(view):
    v = view
    item = saved(v, workflow_id=v.work.workflow_id)
    target = detach(v, item)
    before = v.repo.path.read_bytes()
    assert v.client.get(target).status_code == 405
    assert v.repo.path.read_bytes() == before
    data = form(v.client, listing(v), target)
    data['human_confirmed'] = 'yes'
    response = v.client.post(target, data=data)
    assert response.status_code == 303
    assert v.repo.get_reminder(v.p.project_id, item.reminder_id) == replace(item, workflow_id=None)
    assert v.client.post(target, data=data).status_code == 409


@pytest.mark.parametrize('fault', ['no_human', 'no_token', 'wrong_reminder', 'wrong_project',
    'stale_association', 'foreign_association', 'create_token'])
def test_detach_context_boundary(view, fault):
    v = view
    item = saved(v, workflow_id=v.work.workflow_id)
    target = detach(v, item)
    data = form(v.client, listing(v), target)
    data['human_confirmed'] = 'yes'
    if fault == 'no_human': data.pop('human_confirmed')
    elif fault == 'no_token': data.pop('token')
    elif fault == 'wrong_reminder': target = detach(v, saved(v, workflow_id=v.work.workflow_id))
    elif fault == 'wrong_project': target = target.replace(str(v.p.project_id), str(v.other.project_id))
    elif fault == 'stale_association': v.service.unlink_workflow(v.p.project_id, item.reminder_id, human_confirmed=True)
    elif fault == 'foreign_association':
        with v.repo._connection() as db:
            db.execute('UPDATE reminders SET workflow_id = ? WHERE reminder_id = ?',
                       (str(v.foreign.workflow_id), str(item.reminder_id)))
    else:
        data['token'] = form(v.client, listing(v) + '/new')['token']
    before = v.repo.path.read_bytes()
    assert v.client.post(target, data=data).status_code in (400, 404, 409)
    assert v.repo.path.read_bytes() == before


@pytest.mark.parametrize('operation', ['list', 'register', 'unlink'])
def test_service_failures_are_not_empty_or_success(view, monkeypatch, operation):
    v = view
    item = saved(v, workflow_id=v.work.workflow_id)
    target = detach(v, item) if operation == 'unlink' else listing(v) + '/new'
    data = form(v.client, listing(v) if operation == 'unlink' else target, target)
    data.update(human_confirmed='yes', text='Text', kind='要検討')
    method = {'list': 'list_for_project', 'register': 'register', 'unlink': 'unlink_workflow'}[operation]
    monkeypatch.setattr(ReminderService, method, lambda *args, **kwargs:
        ReminderResult(False, diagnostics=('private error',)))
    response = v.client.get(listing(v)) if operation == 'list' else v.client.post(target, data=data)
    assert response.status_code == 503
    assert 'private error' not in response.get_data(as_text=True)


def test_existing_provenance_display_and_no_candidate_delete_priority_routes(view, monkeypatch):
    v = view
    item = saved(v)
    monkeypatch.setattr(ReminderService, 'list_for_project', lambda self, p:
        ReminderResult(True, reminders=(replace(item, provenance='ai_proposed_human_saved'),)))
    body = v.client.get(listing(v)).get_data(as_text=True)
    assert 'AI提案をHumanが残すと決めたもの' in body
    assert 'name="priority"' not in body and 'name="provenance"' not in body
    for action in ('delete', 'generate', 'prioritize'):
        assert v.client.post(listing(v) + f'/{item.reminder_id}/{action}').status_code == 404


@pytest.mark.parametrize('location', [None, '', '会社でも自宅でもない自由な場所'])
def test_optional_values_and_candidate_do_not_become_implicit_association(view, location):
    v = view
    target = listing(v) + '/new'
    page = target + '?workflow_id=' + str(v.work.workflow_id)
    data = form(v.client, page)
    data.update(kind='将来構想', text='Future', human_confirmed='yes')
    if location is not None: data['location'] = location
    assert v.client.post(page, data=data).status_code == 303
    item, = v.repo.list_reminders(v.p.project_id)
    assert item.workflow_id is None and item.location == location


def test_new_form_has_no_preselected_classification_or_foreign_workflow(view):
    v = view
    body = v.client.get(listing(v) + '/new').get_data(as_text=True)
    assert '<option value="">選択してください</option>' in body
    assert ' selected' not in body and ' multiple' not in body
    assert str(v.foreign.workflow_id) not in body
    assert 'name="location" type="text"' in body
    assert 'name="provenance"' not in body


def test_unlinked_reminder_has_no_detach_form(view):
    v = view
    item = saved(v)
    assert detach(v, item) not in v.client.get(listing(v)).get_data(as_text=True)


from test_plan_workflow import flow
from test_human_control_workflows import control
from test_human_control_workflow_ui import screen
from test_human_control_resume import files


def test_register_and_detach_leave_actual_application_artifacts_and_execution_untouched(screen):
    c, client = screen
    root = f'/control/projects/{c.project.project_id}/reminders'
    before = files(c.f.tmp_path)
    calls = (list(c.entry.mock_calls), list(c.plans.mock_calls))
    data = form(client, root + '/new')
    data.update(kind='改善案', text='Do not execute this', human_confirmed='yes',
                workflow_id=str(c.work.workflow_id), confirm_workflow='yes')
    assert client.post(root + '/new', data=data).status_code == 303
    item, = c.repository.list_reminders(c.project.project_id)
    target = root + f'/{item.reminder_id}/detach'
    data = form(client, root, target)
    data['human_confirmed'] = 'yes'
    assert client.post(target, data=data).status_code == 303
    assert {k: v for k, v in files(c.f.tmp_path).items() if k != c.db.name} == {
        k: v for k, v in before.items() if k != c.db.name}
    assert calls == (c.entry.mock_calls, c.plans.mock_calls)
    for port in (c.ports.implementation, c.ports.evidence, c.ports.review, c.ports.final):
        assert not port.mock_calls
