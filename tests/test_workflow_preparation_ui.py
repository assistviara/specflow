"""T9 boundary tests: actual entry/Plan contracts, offline AI and no live Git."""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from test_plan_workflow import flow
from test_human_control_workflow_execution_ui import launch, hidden
from human_control.workflow_preparation import (
    PreparationSettings, WorkflowPreparation, lines, new_decision_identity)
from human_control.workflows import WorkflowService
from human_control.projects import ProjectService
from human_control.decision_ui import human_input
from core.approval_validation import validate_approval_result


@pytest.fixture
def prepared(launch):
    x = launch
    root = x.f.tmp_path / 'workflow-root'
    root.mkdir()
    files = {key: Path(x.values[key]) for key in
        ('specification', 'constitution', 'principles', 'decisions', 'plan_template', 'plan_prompt_template')}
    files['prompt_template'] = x.f.prompt.template_path
    files['revision_template'] = x.f.revision.revision_template_path
    settings = PreparationSettings(root, x.f.tmp_path, files)
    x.preparation = WorkflowPreparation(settings)
    x.app.extensions['human_preparation'] = x.preparation
    @x.app.context_processor
    def display():
        return dict(managed_preparation=True, execution_repository=settings.repository)
    return x


def select(x, **changes):
    response = x.client.get(x.base + '/new')
    assert response.status_code == 200
    data = hidden(response, x.base + '/new')
    data.update(specification_choice='configured', name='Human selected work',
                project_description='Approved test task', project_version='1')
    data.update(changes)
    return x.client.post(x.base + '/new', data=data)


def approve(x):
    response = select(x)
    assert response.status_code == 200, response.get_data(as_text=True)
    data = hidden(response, x.base + '/approve-specification')
    data['human_confirmed'] = 'yes'
    return x.client.post(x.base + '/approve-specification', data=data), data


def begin(x):
    response, _ = approve(x)
    assert response.status_code == 200, response.get_data(as_text=True)
    data = hidden(response, x.base + '/start')
    data['human_confirmed'] = 'yes'
    response = x.client.post(x.base + '/start', data=data)
    assert response.status_code == 303, response.get_data(as_text=True)
    work, = x.repo.list_workflows(x.project.project_id)
    return work, response.location, data


def test_get_select_and_approve_never_create_state_or_start_workflow(prepared):
    x = prepared
    before = sorted(str(p) for p in x.f.tmp_path.rglob('*'))
    response = x.client.get(x.base + '/new')
    body = response.get_data(as_text=True)
    for name in ('approval_id', 'approved_at', 'state', 'history', 'plan', 'specification'):
        assert f'name="{name}"' not in body
    assert before == sorted(str(p) for p in x.f.tmp_path.rglob('*'))
    approved, _ = approve(x)
    assert approved.status_code == 200
    assert not x.repo.list_workflows(x.project.project_id)
    assert not list(x.preparation.settings.root.rglob('state.json'))
    x.factory.assert_not_called()
    record, = [json.loads(p.read_text(encoding='utf-8')) for p in x.f.repo.approvals_dir.glob('*.json')
               if p.stem != 'spec-1']
    assert record['decision'] == 'approved'
    assert validate_approval_result(record, str(x.f.spec), 'specification').is_valid


def test_explicit_start_generates_state_and_reaches_existing_plan_wait(prepared):
    x = prepared
    work, url, data = begin(x)
    assert work.approval_id != 'spec-1'
    assert work.state_path != str(x.f.state)
    state = json.loads(Path(work.state_path).read_text())
    assert state['status'] == 'plan_approval_pending'
    assert list(Path(work.history_path).glob('*.json'))
    body = x.client.get(url).get_data(as_text=True)
    for name in ('approval_id', 'approved_at', 'repository', 'implementation_branch', 'codex_prompt', 'review_dir'):
        assert f'name="{name}"' not in body
    assert 'name="tdd_required"' in body
    assert x.client.post(x.base + '/start', data=data).status_code == 409
    assert len(x.repo.list_workflows(x.project.project_id)) == 1
    x.factory.assert_called_once()


@pytest.mark.parametrize('stage', ['approval', 'start'])
def test_stale_specification_refuses_approval_or_start(prepared, stage):
    x = prepared
    if stage == 'approval':
        response = select(x)
        url = x.base + '/approve-specification'
    else:
        response, _ = approve(x)
        url = x.base + '/start'
    data = hidden(response, url)
    data['human_confirmed'] = 'yes'
    x.f.spec.write_text('changed after viewing', encoding='utf-8')
    assert x.client.post(url, data=data).status_code == 409
    assert not list(x.preparation.settings.root.rglob('state.json'))
    assert not x.repo.list_workflows(x.project.project_id)
    x.factory.assert_not_called()


def test_approval_post_is_one_use_across_sessions_and_restart(prepared):
    x = prepared
    response, data = approve(x)
    assert response.status_code == 200
    assert x.client.post(x.base + '/approve-specification', data=data).status_code == 409
    x.preparation.selections.clear()  # No restored preparation Output after restart.
    assert select(x).status_code == 409
    assert not list(x.preparation.settings.root.rglob('state.json'))


def test_no_human_confirmation_no_state_or_approval(prepared):
    x = prepared
    response = select(x)
    data = hidden(response, x.base + '/approve-specification')
    assert x.client.post(x.base + '/approve-specification', data=data).status_code == 409
    assert not list(x.preparation.settings.root.iterdir())


def test_missing_start_confirmation_does_not_create_state(prepared):
    response, _ = approve(prepared)
    data = hidden(response, prepared.base + '/start')
    assert prepared.client.post(prepared.base + '/start', data=data).status_code == 409
    assert not list(prepared.preparation.settings.root.rglob('state.json'))


def test_gate_change_stops_start(prepared):
    x = prepared
    response, _ = approve(x)
    data = hidden(response, x.base + '/start')
    data['human_confirmed'] = 'yes'
    x.projects.update_constitution(x.project.project_id, 'purpose', 'changed')
    assert x.client.post(x.base + '/start', data=data).status_code == 409
    assert not list(x.preparation.settings.root.rglob('state.json'))


def test_approval_write_failure_reserves_attempt_without_retry(prepared, monkeypatch):
    x = prepared
    response = select(x)
    data = hidden(response, x.base + '/approve-specification')
    data['human_confirmed'] = 'yes'
    monkeypatch.setattr(type(x.f.repo), 'save', Mock(side_effect=OSError('disk unavailable')))
    assert x.client.post(x.base + '/approve-specification', data=data).status_code == 409
    assert select(x).status_code == 409
    assert not list(x.preparation.settings.root.rglob('state.json'))


def test_registration_failure_does_not_reinitialize_or_retry(prepared, monkeypatch):
    x = prepared
    response, _ = approve(x)
    data = hidden(response, x.base + '/start')
    data['human_confirmed'] = 'yes'
    monkeypatch.setattr(WorkflowService, 'register', Mock(side_effect=OSError('failed')))
    assert x.client.post(x.base + '/start', data=data).status_code == 503
    state, = x.preparation.settings.root.rglob('state.json')
    before = state.read_bytes()
    assert x.client.post(x.base + '/start', data=data).status_code == 409
    assert select(x).status_code == 409
    assert state.read_bytes() == before
    x.factory.assert_not_called()


def test_plan_cancel_records_system_identity_without_delegating(prepared):
    x = prepared
    work, url, _ = begin(x)
    response = x.client.get(url)
    data = hidden(response, url + '/decide')
    data.update(human_confirmed='yes', human_decision='cancelled', comment='Human stops')
    assert x.client.post(url + '/decide', data=data).status_code == 303
    records = [json.loads(p.read_text(encoding='utf-8')) for p in x.f.repo.approvals_dir.glob('*.json')]
    record, = [r for r in records if r['artifact_type'] == 'implementation_plan']
    assert record['decision'] == 'cancelled'
    assert record['approval_id'] and record['approved_at']
    x.ports.implementation.execute.assert_not_called()


def test_meaning_input_is_converted_without_posted_path_overrides(prepared):
    x = prepared
    work, _, _ = begin(x)
    _, paths = WorkflowService(x.repo).binding(work.project_id, work.workflow_id)
    form = dict(repository='untrusted', implementation_branch='wrong', target_paths='src/a.py\ntests/test_a.py',
        allowed_changes='*.py', forbidden_changes_none='yes', source_paths='src/a.py', test_paths='tests/test_a.py')
    result = x.preparation.delegated_form(work, paths, form)
    assert result['repository'] == str(x.f.tmp_path)
    assert result['implementation_branch'] == 'impl/' + str(work.workflow_id)
    assert json.loads(result['source_paths']) == [str(x.f.tmp_path / 'src' / 'a.py')]
    assert json.loads(result['forbidden_changes']) == []


@pytest.mark.parametrize('value', ['../escape.py', '/absolute.py'])
def test_source_cannot_escape_repository(prepared, value):
    work, _, _ = begin(prepared)
    _, paths = WorkflowService(prepared.repo).binding(work.project_id, work.workflow_id)
    form = dict(target_paths='a.py', allowed_changes='*.py', forbidden_changes_none='yes',
                source_paths=value, test_paths_none='yes')
    with pytest.raises(ValueError):
        prepared.preparation.delegated_form(work, paths, form)


@pytest.mark.parametrize('form', [{}, {'x': 'a', 'x_none': 'yes'}])
def test_missing_or_conflicting_meaning_is_not_inferred(form):
    with pytest.raises(ValueError):
        lines(form, 'x')


def test_final_human_input_generates_identity_and_reference_format(prepared):
    with prepared.app.test_request_context(method='POST', data=dict(human_confirmed='yes',
            decision='Final Approval', reason='Human accepts', references='Review report\nTest evidence')):
        command = human_input()
    assert command.approval_id and command.approved_at
    assert command.references == ('Review report', 'Test evidence')


def test_missing_formal_document_stops_without_creation(prepared):
    prepared.preparation.settings.files['constitution'].unlink()
    assert prepared.client.get(prepared.base + '/new').status_code == 400
    assert not list(prepared.preparation.settings.root.iterdir())


def test_unconfigured_production_preparation_does_not_fall_back_to_path_form(prepared):
    prepared.app.extensions['human_preparation'] = None
    assert prepared.client.get(prepared.base + '/new').status_code == 400


def test_plan_approval_connects_existing_prompt_and_implementation_dto(prepared):
    from application.implementation_workflow import ImplementationWorkflowOutput
    x = prepared
    work, url, _ = begin(x)
    x.ports.implementation.execute.side_effect = lambda command: ImplementationWorkflowOutput(
        command, stop_reason='Offline boundary reached; no real Git')
    data = hidden(x.client.get(url), url + '/decide')
    data.update(human_confirmed='yes', human_decision='approved', comment='Approved scope',
        target_paths='source.py', allowed_changes='*.py', forbidden_changes_none='yes',
        source_paths='source.py', test_paths='test_source.py', tdd_required='yes',
        tdd_rules='Initial FAIL then target/full PASS', completion_conditions='All checks',
        stop_conditions='Ambiguity', execution_result_reporting_requirements='Existing report', review_mode='BATCH')
    assert x.client.post(url + '/decide', data=data).status_code == 303
    x.ports.implementation.execute.assert_called_once()
    command = x.ports.implementation.execute.call_args.args[0]
    assert command.repository == x.f.tmp_path
    assert command.implementation_branch == 'impl/' + str(work.workflow_id)
    assert command.tdd.tdd_required is True
    assert command.upstream.approval_result.approval_valid
    x.ports.evidence.execute.assert_not_called()
    assert x.client.post(url + '/decide', data=data).status_code == 409


def test_saved_approval_tampering_prevents_initial_state(prepared):
    x = prepared
    response, _ = approve(x)
    data = hidden(response, x.base + '/start')
    data['human_confirmed'] = 'yes'
    value, = x.preparation.selections.values()
    record = dict(value['record'], decision='rejected')
    x.f.repo.save(record)
    assert x.client.post(x.base + '/start', data=data).status_code == 409
    assert not list(x.preparation.settings.root.rglob('state.json'))


def test_existing_state_is_never_overwritten(prepared):
    x = prepared
    response, _ = approve(x)
    value, = x.preparation.selections.values()
    state = value['slot'] / 'state.json'
    state.write_text('existing formal data', encoding='utf-8')
    data = hidden(response, x.base + '/start')
    data['human_confirmed'] = 'yes'
    assert x.client.post(x.base + '/start', data=data).status_code == 503
    assert state.read_text(encoding='utf-8') == 'existing formal data'
    x.factory.assert_not_called()


def test_specification_choice_is_not_inferred(prepared):
    assert select(prepared, specification_choice='').status_code == 400
    assert not list(prepared.preparation.settings.root.iterdir())


def test_cross_session_cannot_approve_selection(prepared):
    x = prepared
    response = select(x)
    data = hidden(response, x.base + '/approve-specification')
    data['human_confirmed'] = 'yes'
    other = x.app.test_client()
    assert other.post(x.base + '/approve-specification', data=data).status_code == 409
    assert not list(x.preparation.settings.root.iterdir())


def test_environment_bootstrap_uses_only_explicit_input_set(prepared, monkeypatch):
    from app import create_environment_app
    x = prepared
    env = dict(SPECFLOW_HUMAN_CONTROL_DB=str(x.db), SPECFLOW_OPENAI_MODEL='explicit', OPENAI_API_KEY='test',
               SPECFLOW_EXECUTION_REPOSITORY=str(x.f.tmp_path),
               SPECFLOW_APPROVALS_DIR=str(x.f.repo.approvals_dir),
               SPECFLOW_EVIDENCE_DIR=str(x.f.tmp_path), SPECFLOW_EXECUTION_RECORDS_DIR=str(x.f.tmp_path),
               SPECFLOW_WORKFLOW_ROOT=str(x.preparation.settings.root))
    env.update({'SPECFLOW_INPUT_' + role.upper(): str(path) for role, path in x.preparation.settings.files.items()})
    process = Mock(side_effect=AssertionError('No process in bootstrap'))
    monkeypatch.setattr('subprocess.run', process)
    app = create_environment_app(env)
    assert app.extensions['human_preparation'] is not None
    body = app.test_client().get(x.base + '/new').get_data(as_text=True)
    assert 'specification_choice' in body and 'name="state"' not in body
    process.assert_not_called()
    env.pop('SPECFLOW_INPUT_DECISIONS')
    blocked = create_environment_app(env)
    assert blocked.extensions['human_preparation'] is None
    assert blocked.test_client().get(x.base + '/new').status_code == 400


def test_revision_does_not_ask_for_storage_or_template_paths(prepared):
    from core.ai.ai_response import AIResponse
    x = prepared
    work, url, _ = begin(x)
    data = hidden(x.client.get(url), url + '/decide')
    data.update(human_confirmed='yes', human_decision='revision_requested', comment='Clarify scope')
    assert x.client.post(url + '/decide', data=data).status_code == 303
    response = x.client.get(url)
    body = response.get_data(as_text=True)
    assert 'name="revision_template"' not in body and 'name="revised_plan"' not in body
    data = hidden(response, url + '/revise')
    data['human_confirmed'] = 'yes'
    x.f.plan_ai.run.return_value = AIResponse('### REVISED_IMPLEMENTATION_PLAN\n# Revised\n'
        '### CHANGES\nFixed\n### PREVIOUS_VERSION_CORRESPONDENCE\nPrevious', True)
    assert x.client.post(url + '/revise', data=data).status_code == 303
    files = list(Path(work.state_path).parent.glob('plan-revision-*.md'))
    assert len(files) == 1
