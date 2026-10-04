"""T8 step 7: explicit Human decisions over existing formal contracts."""
import json
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app import create_app
from human_control.workflow_ui import continuity
from test_plan_workflow import flow
from test_human_control_workflows import control
from test_human_control_application_adapter import connected
from test_human_control_workflow_execution_ui import launch, delegated, start, decision
from test_human_control_project_ui import form
from test_human_control_resume import files
from test_git_repository_state_provider import run_git
from application.final_approval_decision import FinalApprovalDecision
from human_control.projects import ProjectService
from pathlib import Path
from application.final_approval_workflow import FinalApprovalWorkflowUseCase
from core.ai.ai_response import AIResponse
from test_classify_review_result import evaluation


def test_common_decision_screen_returns_plan_to_existing_ui_without_writes(launch):
    x = launch
    work, execution_path, _ = start(x)
    path = f'{x.base}/{work.workflow_id}/decisions'
    before = files(x.f.tmp_path)
    response = x.client.get(path)
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert 'なぜ判断が必要か' in body and '判断材料' in body and execution_path in body
    assert files(x.f.tmp_path) == before
    x.ports.plans.decide.assert_not_called()


@pytest.fixture
def waiting(delegated):
    d = delegated
    x = d.x
    repo = x.app.extensions['human_control'].require_repository()
    x.app.extensions['human_continuity'] = continuity(repo, x.f.repo.approvals_dir, x.f.tmp_path / 'evidence')
    original = d.real.runner.run.side_effect
    def committed(**kwargs):
        output = original(**kwargs)
        run_git(d.real.root, 'commit', '-m', 'Disposable step 7 implementation')
        return output
    d.real.runner.run.side_effect = committed
    work, execution_path, _ = start(x)
    response, _ = decision(x, execution_path, 'approved', **d.inputs)
    assert response.status_code == 303
    run = x.app.extensions['human_execution'].runs[work.workflow_id]
    assert run.result.success, run.result.reason
    checkpoint = run.result.outputs[-1].snapshot_path
    path = f'{x.base}/{work.workflow_id}/decisions'
    return SimpleNamespace(**locals())


def final_form(w, choice='Plan Revision', **extra):
    data = form(w.x.client, w.path, w.path + '/final')
    data.update(human_confirmed='yes', decision=choice, reason='Human examined the exact target',
                approval_id='final-step-7', approved_at='2026-10-04T12:00:00+09:00', references='[]', comment='Reviewed')
    data.update(extra)
    return data


def restart(w, *, factory=True):
    w.x.app = create_app(w.x.db, approvals_dir=w.x.f.repo.approvals_dir,
        evidence_dir=w.x.f.tmp_path / 'evidence', execution_factory=w.x.factory if factory else None)
    w.x.app.testing = True
    w.x.client = w.x.app.test_client()


def test_final_get_presents_five_choices_and_validated_materials_without_writes(waiting):
    w = waiting
    before = files(w.x.f.tmp_path)
    body = w.x.client.get(w.path).get_data(as_text=True)
    assert '最終承認' in body and 'Merge' in body and '判断材料' in body
    for choice in FinalApprovalDecision:
        assert choice.value in body
    assert 'source.py' in body and str(w.work.workflow_id) in body
    assert files(w.x.f.tmp_path) == before
    w.d.real.final.resume.assert_not_called()
    w.d.real.git.merge.assert_not_called()


@pytest.mark.parametrize('choice', [item.value for item in FinalApprovalDecision])
def test_explicit_final_decision_reuses_contract_and_never_replays(waiting, choice):
    w = waiting
    adapter = w.run.adapter
    data = final_form(w, choice)
    response = w.x.client.post(w.path + '/final', data=data)
    assert response.status_code == 303
    assert response.location == w.path.removesuffix('/decisions')
    returned = w.x.client.get(response.location).get_data(as_text=True)
    assert '今回のHuman判断' in returned and choice in returned
    actual = w.x.app.extensions['human_control'].outputs.get(w.x.project.project_id, w.work.workflow_id).outputs[-1]
    assert actual.success, actual.stop_reason
    assert w.run.adapter is adapter
    w.d.real.final.resume.assert_called_once()
    assert w.x.client.post(w.path + '/final', data=data).status_code == 409
    body = w.x.client.get(w.path).get_data(as_text=True)
    assert '<form' not in body
    if choice == 'Final Approval':
        assert actual.completed and actual.completion.completed
        assert '正式な完了結果' in body
        w.d.real.git.merge.assert_called_once()
    else:
        assert not actual.completed and actual.routing is not None
        assert choice in body and '返却先' in body and 'Handoff' in body
        w.d.real.git.merge.assert_not_called()
    w.d.real.review.correct.assert_not_called()
    assert w.x.ports.plans.revise.call_count == 0
    assert w.x.ports.entry.execute.call_count == 1


@pytest.mark.parametrize('fault', ['no_token', 'no_human', 'no_decision', 'invalid_decision',
    'no_reason', 'bad_references', 'no_approval_id', 'old_approval_id', 'bad_approval_id', 'no_time'])
def test_invalid_human_input_never_creates_receipt_or_runs_final(waiting, fault):
    w = waiting
    data = final_form(w, 'Final Approval')
    if fault == 'no_token': data.pop('token')
    elif fault == 'no_human': data.pop('human_confirmed')
    elif fault == 'no_decision': data['decision'] = ''
    elif fault == 'invalid_decision': data['decision'] = 'Automatically approved'
    elif fault == 'no_reason': data['reason'] = ' '
    elif fault == 'bad_references': data['references'] = '{}'
    elif fault == 'no_approval_id': data['approval_id'] = ''
    elif fault == 'old_approval_id': data['approval_id'] = 'spec-1'
    elif fault == 'bad_approval_id': data['approval_id'] = '../outside'
    else: data['approved_at'] = ''
    before = files(w.x.f.tmp_path)
    assert w.x.client.post(w.path + '/final', data=data).status_code in (400, 409)
    assert files(w.x.f.tmp_path) == before
    w.d.real.final.resume.assert_not_called()
    w.d.real.git.merge.assert_not_called()


@pytest.mark.parametrize('fault', ['spec', 'plan', 'checkpoint', 'target', 'approval', 'state', 'history',
    'constitution', 'evidence', 'receipt'])
def test_changed_formal_target_rejects_stale_post(waiting, fault):
    w = waiting
    data = final_form(w)
    paths = w.x.repo.artifact_references(w.work.workflow_id)
    if fault == 'spec': w.x.f.spec.write_text('Changed')
    elif fault == 'plan': w.x.f.plan_path.write_text('Changed')
    elif fault == 'checkpoint': w.checkpoint.write_text('{}')
    elif fault == 'target': w.run.result.outputs[-1].target.request.artifact_path.write_text('{}')
    elif fault == 'approval': w.x.f.repo.save({**w.x.f.repo.get('spec-1'), 'decision':'rejected'})
    elif fault == 'state': w.x.f.state.write_text('{"status":"completed"}')
    elif fault == 'history': (w.x.history / 'changed.json').write_text('{}')
    elif fault == 'constitution': w.x.projects.update_constitution(w.x.project.project_id, 'purpose', 'New purpose')
    elif fault == 'evidence': Path(paths['evidence']).write_text('{}')
    else: w.checkpoint.with_suffix('.decision.json').write_text('{}')
    before = files(w.x.f.tmp_path)
    assert w.x.client.post(w.path + '/final', data=data).status_code == 409
    assert files(w.x.f.tmp_path) == before
    w.d.real.final.resume.assert_not_called()


@pytest.mark.parametrize('fault', ['foreign_project', 'wrong_workflow', 'another_session'])
def test_final_identity_and_session_boundary(waiting, fault):
    w = waiting
    data = final_form(w)
    path, client = w.path + '/final', w.x.client
    if fault == 'foreign_project':
        other = w.x.projects.create('Same name')
        path = path.replace(str(w.x.project.project_id), str(other.project_id))
    elif fault == 'wrong_workflow': path = path.replace(str(w.work.workflow_id), str(uuid4()))
    else: client = w.x.app.test_client()
    before = files(w.x.f.tmp_path)
    assert client.post(path, data=data).status_code in (404, 409)
    assert files(w.x.f.tmp_path) == before
    w.d.real.final.resume.assert_not_called()


@pytest.mark.parametrize('choice', ['Final Approval', 'Plan Revision'])
def test_restart_uses_only_existing_final_checkpoint_without_restarting_work(waiting, choice):
    w = waiting
    restart(w)
    before = files(w.x.f.tmp_path)
    data = final_form(w, choice)
    assert files(w.x.f.tmp_path) == before
    assert not w.x.app.extensions['human_execution'].runs
    assert w.x.client.post(w.path + '/final', data=data).status_code == 303
    actual = w.x.app.extensions['human_control'].outputs.get(w.x.project.project_id, w.work.workflow_id)
    assert len(actual.outputs) == 1 and actual.outputs[0].success, actual
    assert not w.x.app.extensions['human_execution'].runs
    w.x.ports.entry.execute.assert_called_once()
    w.x.ports.plans.generate.assert_called_once()
    w.d.real.final.start.assert_called_once()
    w.d.real.final.resume.assert_called_once()
    assert w.x.client.post(w.path + '/final', data=data).status_code == 409


def test_restart_missing_execution_dependency_is_read_only_stop(waiting):
    w = waiting
    restart(w, factory=False)
    before = files(w.x.f.tmp_path)
    body = w.x.client.get(w.path).get_data(as_text=True)
    assert 'STOP' in body and '<form' not in body
    assert files(w.x.f.tmp_path) == before
    w.d.real.final.resume.assert_not_called()


def test_constitution_change_handoff_never_transitions_formal_state(launch):
    x = launch
    work, execution_path, _ = start(x)
    x.projects.update_constitution(x.project.project_id, 'purpose', 'Changed purpose')
    path = f'{x.base}/{work.workflow_id}/decisions'
    before = files(x.f.tmp_path)
    body = x.client.get(path).get_data(as_text=True)
    assert 'Changed purpose' in body and '影響判断' in body and '再確認待ち' in body
    assert '継続・停止・再検討' in body
    assert files(x.f.tmp_path) == before
    assert not x.projects.workflow_start_gate(x.project.project_id).allowed
    x.projects.confirm_constitution(x.project.project_id, 'purpose', 'Changed purpose', human_confirmed=True)
    body = x.client.get(path).get_data(as_text=True)
    assert '再確認だけでは影響判断済みになりません' in body
    assert json.loads(x.f.state.read_text())['status'] == 'plan_approval_pending'
    x.ports.plans.decide.assert_not_called()


@pytest.mark.parametrize('fault', ['receipt', 'approval', 'history', 'result', 'index', 'holder', 'merge'])
def test_partial_failure_stops_retains_actual_results_and_never_retries(waiting, monkeypatch, fault):
    w = waiting
    choice = 'Plan Revision' if fault in ('result', 'index', 'holder') else 'Final Approval'
    data = final_form(w, choice)
    if fault in ('receipt', 'result'):
        original = FinalApprovalWorkflowUseCase._save_event
        def failing(path, value):
            if ((fault == 'receipt' and path.name.endswith('.decision.json'))
                    or (fault == 'result' and path.name.startswith('final_result_'))):
                raise OSError('Test persistence failure')
            return original(path, value)
        monkeypatch.setattr(FinalApprovalWorkflowUseCase, '_save_event', staticmethod(failing))
    elif fault == 'approval':
        monkeypatch.setattr(w.x.f.repo, 'save', Mock(side_effect=OSError('Approval storage unavailable')))
    elif fault == 'history':
        monkeypatch.setattr('application.state_transition.save_state_transition_history',
                            Mock(side_effect=OSError('History storage unavailable')))
    elif fault == 'index':
        monkeypatch.setattr(w.x.app.extensions['human_control'].require_repository(), 'set_artifact_references',
                            Mock(side_effect=OSError('Index storage unavailable')))
    elif fault == 'holder':
        monkeypatch.setattr(w.x.app.extensions['human_control'].outputs, 'put',
                            Mock(side_effect=ValueError('Output unavailable')))
    else: w.d.real.git.merge.side_effect = OSError('Git execution failed')
    assert w.x.client.post(w.path + '/final', data=data).status_code == 303
    actual = w.run.adapter.observation().outputs[-1]
    assert actual.snapshot_path == w.checkpoint
    assert not w.run.result.success or w.run.failure
    body = w.x.client.get(w.path).get_data(as_text=True)
    assert 'STOP' in body and '<form' not in body
    assert '正式な完了結果を保持しています' not in body
    assert w.x.client.post(w.path + '/final', data=data).status_code == 409
    w.d.real.final.resume.assert_called_once()
    w.d.real.final.retry.assert_not_called()
    w.d.real.git.retry_merge.assert_not_called()
    if fault == 'history':
        assert json.loads(w.x.f.state.read_text())['status'] == 'completed'
        assert not actual.completed
        assert '返却先の処理は自動実行していません' not in body
    if fault in ('history', 'merge'): w.d.real.git.merge.assert_called_once()
    else: w.d.real.git.merge.assert_not_called()


@pytest.mark.parametrize('fault', ['factory', 'incomplete_ports', 'changed_during_factory',
    'constitution_during_factory', 'index', 'holder'])
def test_restart_execution_failure_retains_attempt_without_reentry(waiting, monkeypatch, fault):
    w = waiting
    restart(w)
    data = final_form(w)
    if fault == 'factory': w.x.factory.side_effect = OSError('Dependency unavailable')
    elif fault == 'incomplete_ports': w.x.factory.return_value = None
    elif fault == 'changed_during_factory':
        def factory(*args):
            w.x.f.spec.write_text('Changed while constructing ports')
            return w.d.real.ports
        w.x.factory.side_effect = factory
    elif fault == 'constitution_during_factory':
        def factory(*args):
            w.x.projects.update_constitution(w.x.project.project_id, 'purpose', 'Changed during composition')
            return w.d.real.ports
        w.x.factory.side_effect = factory
    elif fault == 'index':
        monkeypatch.setattr(w.x.app.extensions['human_control'].require_repository(), 'set_artifact_references',
                            Mock(side_effect=OSError('Index unavailable')))
    else:
        monkeypatch.setattr(w.x.app.extensions['human_control'].outputs, 'put',
                            Mock(side_effect=ValueError('Output unavailable')))
    assert w.x.client.post(w.path + '/final', data=data).status_code == 303
    body = w.x.client.get(w.path).get_data(as_text=True)
    assert 'STOP' in body and '<form' not in body
    assert w.x.client.post(w.path + '/final', data=data).status_code == 409
    if fault in ('index', 'holder'):
        w.d.real.final.resume.assert_called_once()
        assert w.x.app.extensions['human_decisions'][w.work.workflow_id].output is not None
    else: w.d.real.final.resume.assert_not_called()
    w.x.ports.entry.execute.assert_called_once()
    w.d.real.git.merge.assert_not_called()


@pytest.mark.parametrize('artifact', ['checkpoint', 'evidence', 'approval'])
def test_restart_missing_artifact_never_offers_final_post(waiting, artifact):
    w = waiting
    if artifact == 'checkpoint': w.checkpoint.unlink()
    elif artifact == 'evidence': Path(w.x.repo.artifact_references(w.work.workflow_id)['evidence']).unlink()
    else: (w.x.f.repo.approvals_dir / 'spec-1.json').unlink()
    restart(w)
    before = files(w.x.f.tmp_path)
    body = w.x.client.get(w.path).get_data(as_text=True)
    assert 'STOP' in body and '<form' not in body
    assert files(w.x.f.tmp_path) == before
    w.d.real.final.resume.assert_not_called()


@pytest.mark.parametrize('choice', ['Plan Revision', 'Cancellation'])
def test_recorded_return_after_restart_is_handoff_not_reexecution(waiting, choice):
    w = waiting
    data = final_form(w, choice)
    assert w.x.client.post(w.path + '/final', data=data).status_code == 303
    restart(w)
    before = files(w.x.f.tmp_path)
    body = w.x.client.get(w.path).get_data(as_text=True)
    assert choice in body and '返却先' in body and 'Handoff' in body
    assert '<form' not in body
    assert files(w.x.f.tmp_path) == before
    w.d.real.final.resume.assert_called_once()
    w.d.real.git.merge.assert_not_called()


def test_review_human_handoff_common_screen_has_no_invented_actions(delegated):
    d = delegated
    x = d.x
    x.app.extensions['human_continuity'] = continuity(x.app.extensions['human_control'].require_repository(),
        x.f.repo.approvals_dir, x.f.tmp_path / 'evidence')
    original = d.real.ai.run.side_effect
    def review(request):
        if request.prompt.startswith('# Review Result Evaluation'):
            output = evaluation('HUMAN_REVIEW_REQUIRED')
            output['references'] = ['review.prepared.review_input.implementation_plan.content']
            output['human_questions'] = ['Human must clarify this behavior']
            return AIResponse(json.dumps(output), True)
        return original(request)
    d.real.ai.run.side_effect = review
    work, path, _ = start(x)
    assert decision(x, path, 'approved', **d.inputs)[0].status_code == 303
    before = files(x.f.tmp_path)
    body = x.client.get(f'{x.base}/{work.workflow_id}/decisions').get_data(as_text=True)
    assert 'Human must clarify this behavior' in body and 'Handoff' in body
    assert '<form' not in body and files(x.f.tmp_path) == before
    d.real.review.correct.assert_not_called()
    d.real.final.start.assert_not_called()
    d.real.git.merge.assert_not_called()
