"""T8 internal unit 6, exercising existing Phase 7 through web requests."""
from test_human_control_project_ui import ui, form
from test_plan_workflow import flow
from test_human_control_workflows import control
from test_human_control_application_adapter import connected
from test_human_control_resume import files
from test_human_control_projects import confirm_all
from app import create_app
from human_control.sqlite_repository import HumanControlRepository
from human_control.projects import ProjectService
from human_control.application_adapter import ApplicationPorts
from application.workflow_entry import WorkflowEntryUseCase
from core.ai.ai_response import AIResponse
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4
import hashlib
import json
import re
import html
import pytest
from test_classify_review_result import evaluation



def hidden(response, action):
    body = response.get_data(as_text=True)
    chosen = next(f for f in re.findall(r'<form.*?</form>', body, re.S) if f'action="{action}"' in f)
    return {k: html.unescape(v) for k, v in re.findall(
        r'<input type="hidden" name="([^"]+)" value="([^"]*)"', chosen)}


@pytest.fixture
def launch(flow):
    f = flow
    f.state.write_text('{"status":"specification_ready"}')
    history = f.tmp_path / 'web-history'
    for path in (f.generation.constitution_path, f.generation.principles_path,
                 f.generation.decisions_path, f.generation.implementation_plan_template_path,
                 f.generation.template_path, f.prompt.template_path, f.revision.revision_template_path):
        path.write_text('Explicit formal input')
    db = f.tmp_path / 'web.db'
    HumanControlRepository.initialize(db)
    repo = HumanControlRepository(db)
    projects = ProjectService(repo)
    project = projects.create('Web Project')
    confirm_all(projects, project)
    ports = ApplicationPorts(Mock(wraps=WorkflowEntryUseCase(f.repo)), Mock(wraps=f.use_case),
                             Mock(), Mock(), Mock(), Mock())
    factory = Mock(return_value=ports)
    app = create_app(db, approvals_dir=f.repo.approvals_dir, execution_factory=factory)
    app.testing = True
    client = app.test_client()
    base = f'/control/projects/{project.project_id}/workflows'
    values = dict(name='Human work', specification=str(f.spec), approval_id='spec-1',
        state=str(f.state), history=str(history), constitution=str(f.generation.constitution_path),
        principles=str(f.generation.principles_path), decisions=str(f.generation.decisions_path),
        plan_template=str(f.generation.implementation_plan_template_path),
        plan_prompt_template=str(f.generation.template_path), plan=str(f.plan_path),
        project_name='Formal Project', target_path=str(f.tmp_path), project_description='Explicit', project_version='1')
    return SimpleNamespace(**locals())


def preview(x, **changes):
    data = form(x.client, x.base + '/new')
    data.update(x.values)
    data.update(changes)
    return x.client.post(x.base + '/new', data=data)


def start(x):
    response = preview(x)
    assert response.status_code == 200, response.get_data(as_text=True)
    data = hidden(response, x.base + '/start')
    data['human_confirmed'] = 'yes'
    response = x.client.post(x.base + '/start', data=data)
    assert response.status_code == 303, response.get_data(as_text=True)
    work, = x.repo.list_workflows(x.project.project_id)
    return work, response.location, data


def decision(x, path, choice, **extra):
    data = form(x.client, path, path + '/decide')
    data.update(human_confirmed='yes', human_decision=choice, approval_id='web-plan-1',
                approved_at='2026-10-04', comment='Human judgment')
    data.update(extra)
    return x.client.post(path + '/decide', data=data), data


def test_project_offers_explicit_workflow_start_without_get_side_effects(ui):
    client, repo, projects, _ = ui
    project = projects.create('Project')
    before = repo.path.read_bytes()
    path = f'/control/projects/{project.project_id}/workflows/new'
    assert path in client.get(f'/control/projects/{project.project_id}').get_data(as_text=True)
    assert client.get(path).status_code == 200
    assert repo.path.read_bytes() == before


def test_start_saves_actual_plan_and_retains_same_adapter_and_output(launch):
    x = launch
    constitution = x.f.generation.constitution_path.read_bytes()
    work, path, data = start(x)
    runtime = x.app.extensions['human_control']
    run = x.app.extensions['human_execution'].runs[work.workflow_id]
    assert work.specification_hash == hashlib.sha256(x.f.spec.read_bytes()).hexdigest()
    assert x.f.plan_path.is_file()
    assert work.name == 'Human work'
    assert x.f.generation.constitution_path.read_bytes() == constitution
    assert runtime.outputs.get(x.project.project_id, work.workflow_id) == run.adapter.observation()
    assert len(run.adapter.observation().outputs) == 2
    before = files(x.f.tmp_path)
    body = x.client.get(path).get_data(as_text=True)
    assert 'Human review required.' in body and '計画の判断を待っています' in body
    assert files(x.f.tmp_path) == before
    assert x.client.post(x.base + '/start', data=data).status_code == 409
    assert x.app.extensions['human_execution'].runs[work.workflow_id].adapter is run.adapter
    x.ports.entry.execute.assert_called_once()
    x.ports.plans.generate.assert_called_once()
    x.ports.plans.decide.assert_not_called()
    x.factory.assert_called_once()


@pytest.mark.parametrize('fault', ['gate', 'missing_spec', 'pattern', 'relative', 'missing_approval_id',
    'missing_document', 'missing_metadata', 'missing_state', 'missing_dependency'])
def test_start_input_failure_never_registers_or_executes(launch, fault):
    x = launch
    changes = {}
    if fault == 'gate': x.projects.update_constitution(x.project.project_id, 'purpose', 'Changed')
    elif fault == 'missing_spec': changes['specification'] = str(x.f.tmp_path / 'missing')
    elif fault == 'pattern': changes['specification'] = str(x.f.tmp_path / '*.md')
    elif fault == 'relative': changes['specification'] = 'spec.md'
    elif fault == 'missing_approval_id': changes['approval_id'] = ''
    elif fault == 'missing_document': changes['constitution'] = ''
    elif fault == 'missing_metadata': changes['project_version'] = ''
    elif fault == 'missing_state': changes['state'] = str(x.f.tmp_path / 'missing-state')
    else: x.app.extensions['human_execution'].factory = None
    before = files(x.f.tmp_path)
    response = preview(x, **changes)
    assert response.status_code in (400, 409, 503)
    assert not x.repo.list_workflows(x.project.project_id)
    assert files(x.f.tmp_path) == before
    x.ports.entry.execute.assert_not_called()


@pytest.mark.parametrize('fault', ['spec_stale', 'gate_stale', 'wrong_project', 'no_token', 'no_human', 'input_changed'])
def test_confirm_start_rejects_stale_and_wrong_context(launch, fault):
    x = launch
    data = hidden(preview(x), x.base + '/start')
    data['human_confirmed'] = 'yes'
    target = x.base + '/start'
    if fault == 'spec_stale': x.f.spec.write_text('Changed bytes')
    elif fault == 'gate_stale': x.projects.update_constitution(x.project.project_id, 'purpose', 'Changed')
    elif fault == 'wrong_project':
        p = x.projects.create('Other')
        confirm_all(x.projects, p)
        target = target.replace(str(x.project.project_id), str(p.project_id))
    elif fault == 'no_token': data.pop('token')
    elif fault == 'no_human': data.pop('human_confirmed')
    else: data['name'] = 'Tampered'
    before = files(x.f.tmp_path)
    assert x.client.post(target, data=data).status_code in (400, 409)
    assert files(x.f.tmp_path) == before
    x.ports.entry.execute.assert_not_called()


@pytest.mark.parametrize('fault', ['approval_missing', 'approval_invalid', 'state_invalid', 'plan_failure', 'binding'])
def test_registered_failure_is_not_success_rollback_or_retry(launch, fault):
    x = launch
    if fault == 'approval_missing': (x.f.repo.approvals_dir / 'spec-1.json').unlink()
    elif fault == 'approval_invalid': x.f.repo.save({**x.f.repo.get('spec-1'), 'decision':'rejected'})
    elif fault == 'state_invalid': x.f.state.write_text('{"status":"completed"}')
    elif fault == 'plan_failure': x.f.plan_ai.run.return_value = AIResponse('', False, 'Runner stopped')
    else:
        def factory(*args):
            x.f.spec.write_text('Changed after registration')
            return x.ports
        x.app.extensions['human_execution'].factory = factory
    work, path, data = start(x)
    body = x.client.get(path).get_data(as_text=True)
    assert 'STOP' in body and '登録済み' in body
    assert len(x.repo.list_workflows(x.project.project_id)) == 1
    assert x.client.post(x.base + '/start', data=data).status_code == 409
    assert x.ports.entry.execute.call_count <= 1
    x.ports.implementation.execute.assert_not_called()


def test_missing_delegation_never_saves_approval(launch):
    x = launch
    _, path, _ = start(x)
    before = files(x.f.tmp_path)
    response, _ = decision(x, path, 'approved')
    assert response.status_code == 400
    assert files(x.f.tmp_path) == before
    x.ports.plans.decide.assert_not_called()


@pytest.mark.parametrize('choice', ['revision_requested', 'cancelled'])
def test_explicit_plan_decisions_and_replay(launch, choice):
    x = launch
    _, path, _ = start(x)
    response, data = decision(x, path, choice)
    assert response.status_code == 303
    assert x.f.repo.get('web-plan-1')['decision'] == choice
    assert x.client.post(path + '/decide', data=data).status_code == 409
    x.ports.implementation.execute.assert_not_called()


@pytest.mark.parametrize('fault', ['plan_changed', 'spec_changed', 'wrong_workflow', 'foreign_project',
    'no_human', 'invalid_choice', 'no_token'])
def test_plan_decision_boundary(launch, fault):
    x = launch
    work, path, _ = start(x)
    data = form(x.client, path, path + '/decide')
    data.update(human_confirmed='yes', human_decision='cancelled', approval_id='web-plan-1', approved_at='2026-10-04')
    target = path + '/decide'
    if fault == 'plan_changed': x.f.plan_path.write_text('Changed')
    elif fault == 'spec_changed': x.f.spec.write_text('Changed')
    elif fault == 'wrong_workflow': target = target.replace(str(work.workflow_id), str(uuid4()))
    elif fault == 'foreign_project':
        p = x.projects.create('Other')
        target = target.replace(str(x.project.project_id), str(p.project_id))
    elif fault == 'no_human': data.pop('human_confirmed')
    elif fault == 'no_token': data.pop('token')
    else: data['human_decision'] = 'AI approved'
    before = files(x.f.tmp_path)
    assert x.client.post(target, data=data).status_code in (400, 404, 409)
    assert files(x.f.tmp_path) == before
    x.ports.plans.decide.assert_not_called()


def test_revision_uses_same_adapter_new_artifact_and_waits_again(launch):
    x = launch
    work, path, _ = start(x)
    original = x.f.plan_path.read_bytes()
    assert decision(x, path, 'revision_requested')[0].status_code == 303
    x.f.plan_ai.run.return_value = AIResponse('### REVISED_IMPLEMENTATION_PLAN\n# Revised\n'
        '### CHANGES\nFixed\n### PREVIOUS_VERSION_CORRESPONDENCE\nPrevious', True)
    data = form(x.client, path, path + '/revise')
    data.update(human_confirmed='yes', revision_template=str(x.f.revision.revision_template_path),
                revised_plan=str(x.f.tmp_path / 'revised.md'), related_information='')
    assert x.client.post(path + '/revise', data=data).status_code == 303
    assert x.f.plan_path.read_bytes() == original
    assert (x.f.tmp_path / 'revised.md').is_file()
    assert '計画の判断を待っています' in x.client.get(path).get_data(as_text=True)
    x.ports.plans.revise.assert_called_once()
    assert x.client.post(path + '/revise', data=data).status_code == 409


def test_restart_never_reconstructs_adapter_or_reexecutes(launch):
    x = launch
    work, path, _ = start(x)
    app = create_app(x.db, approvals_dir=x.f.repo.approvals_dir, execution_factory=x.factory)
    response = app.test_client().get(path)
    assert 'STOP' in response.get_data(as_text=True)
    assert not app.extensions['human_execution'].runs
    assert app.extensions['human_control'].outputs.get(x.project.project_id, work.workflow_id) is None
    x.factory.assert_called_once()
    x.ports.entry.execute.assert_called_once()


@pytest.fixture
def delegated(launch, connected):
    x, real = launch, connected
    x.ports = real.ports
    x.factory.return_value = real.ports
    inputs = dict(repository=str(real.root), implementation_target=str(real.root),
        implementation_branch='impl/t8-6', prompt_template=str(x.f.prompt.template_path),
        codex_prompt=str(x.f.tmp_path / 'web-prompt.md'), review_dir=str(x.f.tmp_path / 'web-review'),
        final_dir=str(x.f.tmp_path / 'web-final'), tdd_rules='TDD', completion_conditions='Complete',
        stop_conditions='Stop', execution_result_reporting_requirements='Report',
        target_paths='["source.py", "test_source.py"]', allowed_changes='["*.py"]', forbidden_changes='[]',
        source_paths=json.dumps([str(real.root / 'source.py')]),
        test_paths=json.dumps([str(real.root / 'test_source.py')]), tdd_required='yes', review_mode='BATCH')
    return SimpleNamespace(x=x, real=real, inputs=inputs)


def test_human_approval_delegates_to_final_wait_in_one_request(delegated):
    d = delegated
    x, real = d.x, d.real
    work, path, _ = start(x)
    adapter = x.app.extensions['human_execution'].runs[work.workflow_id].adapter
    response, data = decision(x, path, 'approved', **d.inputs)
    assert response.status_code == 303
    run = x.app.extensions['human_execution'].runs[work.workflow_id]
    assert run.adapter is adapter and run.result.success, run.result.reason
    assert run.result.waiting_for_human and not run.result.outputs[-1].completed
    assert run.result.outputs[-1].waiting_for_human
    assert json.loads(x.f.state.read_text())['status'] == 'final_approval_pending'
    for port, method in ((real.implementation, 'execute'), (real.evidence, 'execute'),
                         (real.review, 'start'), (real.final, 'start')):
        getattr(port, method).assert_called_once()
    assert x.app.extensions['human_control'].outputs.get(x.project.project_id, work.workflow_id) == adapter.observation()
    before = files(x.f.tmp_path)
    body = x.client.get(path).get_data(as_text=True)
    assert '人の確認・判断を待っています' in body and '<form' not in body
    assert files(x.f.tmp_path) == before
    assert x.client.post(path + '/decide', data=data).status_code == 409
    real.final.resume.assert_not_called()
    real.review.correct.assert_not_called()
    real.git.merge.assert_not_called()
    x.factory.assert_called_once()


@pytest.mark.parametrize('fault', ['scope', 'sources', 'outside', 'mode', 'tdd', 'no_tdd_reason',
    'prompt_template', 'branch', 'prompt_destination'])
def test_invalid_delegated_input_stops_before_human_approval(delegated, fault):
    d = delegated
    x = d.x
    _, path, _ = start(x)
    if fault == 'scope': d.inputs.pop('target_paths')
    elif fault == 'sources': d.inputs['source_paths'] = 'not a JSON array'
    elif fault == 'outside': d.inputs['source_paths'] = json.dumps([str(x.f.spec)])
    elif fault == 'mode': d.inputs['review_mode'] = 'AUTO'
    elif fault == 'tdd': d.inputs.pop('tdd_required')
    elif fault == 'no_tdd_reason': d.inputs['tdd_required'] = 'no'
    elif fault == 'prompt_template': d.inputs['prompt_template'] = str(x.f.tmp_path / 'missing.md')
    elif fault == 'branch': d.inputs['implementation_branch'] = ''
    else: d.inputs['codex_prompt'] = str(x.f.spec)
    before = files(x.f.tmp_path)
    response, data = decision(x, path, 'approved', **d.inputs)
    assert response.status_code == 400
    assert files(x.f.tmp_path) == before
    x.ports.plans.decide.assert_not_called()
    d.real.runner.run.assert_not_called()
    assert x.client.post(path + '/decide', data=data).status_code == 409


def test_human_review_handoff_is_display_only(delegated):
    d = delegated
    original = d.real.ai.run.side_effect
    def response(request):
        if request.prompt.startswith('# Review Result Evaluation'):
            data = evaluation('HUMAN_REVIEW_REQUIRED')
            data['references'] = ['review.prepared.review_input.implementation_plan.content']
            data['human_questions'] = ['Human must clarify the behavior']
            return AIResponse(json.dumps(data), True)
        return original(request)
    d.real.ai.run.side_effect = response
    work, path, _ = start(d.x)
    assert decision(d.x, path, 'approved', **d.inputs)[0].status_code == 303
    run = d.x.app.extensions['human_execution'].runs[work.workflow_id]
    assert run.result.success, run.result.reason
    assert run.result.outputs[-1].waiting_for_human
    body = d.x.client.get(path).get_data(as_text=True)
    assert 'Human must clarify the behavior' in body and '<form' not in body
    d.real.review.correct.assert_not_called()
    d.real.final.start.assert_not_called()
    d.real.git.merge.assert_not_called()


@pytest.mark.parametrize('fault', ['prompt', 'implementation', 'reference_persistence', 'prompt_persistence'])
def test_downstream_failure_retains_output_and_does_not_retry(delegated, monkeypatch, fault):
    d = delegated
    x = d.x
    work, path, _ = start(x)
    if fault == 'prompt': x.f.prompt_ai.run.return_value = AIResponse('', False, 'Failure')
    elif fault == 'implementation': d.real.implementation.execute.side_effect = OSError('Execution failed')
    elif fault == 'reference_persistence':
        repo = x.app.extensions['human_control'].require_repository()
        original = repo.set_artifact_references
        def failed(identity, refs):
            if 'test_execution_record' in refs: raise OSError('disk full')
            return original(identity, refs)
        monkeypatch.setattr(repo, 'set_artifact_references', failed)
    else:
        d.inputs['codex_prompt'] = str(x.f.tmp_path / 'nonexistent-parent' / 'prompt.md')
    response, data = decision(x, path, 'approved', **d.inputs)
    assert response.status_code == 303
    run = x.app.extensions['human_execution'].runs[work.workflow_id]
    assert not run.result.success
    assert run.result.outputs
    assert x.f.repo.get('web-plan-1')['decision'] == 'approved'
    assert 'STOP' in x.client.get(path).get_data(as_text=True)
    assert x.client.post(path + '/decide', data=data).status_code == 409
    d.real.evidence.execute.assert_not_called()
    d.real.git.merge.assert_not_called()


@pytest.mark.parametrize('fault', ['factory', 'plan_persistence', 'history_persistence'])
def test_start_partial_failure_has_no_automatic_retry(launch, monkeypatch, fault):
    x = launch
    if fault == 'factory': x.factory.side_effect = OSError('Dependency unavailable')
    elif fault == 'plan_persistence': x.values['plan'] = str(x.f.tmp_path / 'absent' / 'plan.md')
    else:
        from pathlib import Path
        original = Path.mkdir
        def fail_history(path, *args, **kwargs):
            if path == x.history: raise OSError('History storage failed')
            return original(path, *args, **kwargs)
        monkeypatch.setattr(Path, 'mkdir', fail_history)
    work, path, data = start(x)
    assert 'STOP' in x.client.get(path).get_data(as_text=True)
    assert x.repo.get_workflow(work.workflow_id) == work
    assert x.client.post(x.base + '/start', data=data).status_code == 409
    x.ports.implementation.execute.assert_not_called()


def test_new_request_with_same_spec_is_not_deduplicated(launch):
    x = launch
    first, _, _ = start(x)
    state = x.f.tmp_path / 'second-state.json'
    state.write_text('{"status":"specification_ready"}')
    x.values.update(state=str(state), history=str(x.f.tmp_path / 'second-history'), plan=str(x.f.tmp_path / 'second-plan.md'))
    data = hidden(preview(x), x.base + '/start')
    response = x.client.post(x.base + '/start', data={**data, 'human_confirmed':'yes'})
    assert response.status_code == 303
    works = x.repo.list_workflows(x.project.project_id)
    assert len(works) == 2 and works[0].workflow_id != works[1].workflow_id
    assert {w.specification_hash for w in works} == {first.specification_hash}
    assert x.ports.entry.execute.call_count == 2


@pytest.mark.parametrize('fault', ['approval', 'state', 'history'])
def test_saved_approval_and_formal_state_changes_invalidate_decision(launch, fault):
    x = launch
    _, path, _ = start(x)
    data = form(x.client, path, path + '/decide')
    data.update(human_confirmed='yes', human_decision='cancelled', approval_id='web-plan-1', approved_at='2026-10-04')
    if fault == 'approval': x.f.repo.save({**x.f.repo.get('spec-1'), 'comment':'Changed externally'})
    elif fault == 'state': x.f.state.write_text('{"status":"completed"}')
    else: (x.history / 'external.json').write_text('{}')
    before = files(x.f.tmp_path)
    assert x.client.post(path + '/decide', data=data).status_code == 409
    assert '<form' not in x.client.get(path).get_data(as_text=True)
    assert files(x.f.tmp_path) == before


def test_start_registration_failure_consumes_token_before_write(launch, monkeypatch):
    x = launch
    data = hidden(preview(x), x.base + '/start')
    data['human_confirmed'] = 'yes'
    repo = x.app.extensions['human_control'].require_repository()
    write = Mock(side_effect=OSError('database locked'))
    monkeypatch.setattr(repo, 'register_workflow', write)
    assert x.client.post(x.base + '/start', data=data).status_code == 503
    assert x.client.post(x.base + '/start', data=data).status_code == 409
    write.assert_called_once()
    x.ports.entry.execute.assert_not_called()
    assert not x.repo.list_workflows(x.project.project_id)


def test_token_is_not_transferable_to_another_session(launch):
    x = launch
    data = hidden(preview(x), x.base + '/start')
    data['human_confirmed'] = 'yes'
    assert x.app.test_client().post(x.base + '/start', data=data).status_code == 409
    assert not x.repo.list_workflows(x.project.project_id)


def test_incomplete_application_ports_never_enter_phase7(launch):
    x = launch
    x.factory.return_value = ApplicationPorts(x.ports.entry, x.ports.plans, None, None, None, None)
    _, path, _ = start(x)
    assert 'STOP' in x.client.get(path).get_data(as_text=True)
    x.ports.entry.execute.assert_not_called()


def test_output_holder_failure_retains_adapter_and_stops(launch, monkeypatch):
    x = launch
    holder = x.app.extensions['human_control'].outputs
    monkeypatch.setattr(holder, 'put', Mock(side_effect=ValueError('Output unavailable')))
    work, path, _ = start(x)
    run = x.app.extensions['human_execution'].runs[work.workflow_id]
    assert len(run.adapter.observation().outputs) == 2
    body = x.client.get(path).get_data(as_text=True)
    assert 'STOP' in body and '<form' not in body
    x.ports.entry.execute.assert_called_once()
