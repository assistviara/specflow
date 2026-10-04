"""Read-only T5 projection and explicit T6 management actions. No execution."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from application.final_approval_workflow import FinalApprovalWorkflowUseCase
from human_control.end_work import EndWorkService
from human_control.projects import ProjectService
from human_control.resume import ResumeService
from human_control.web_runtime import BoundaryError
from human_control.workflows import WorkflowService
from infrastructure.json_approval_record_repository import JsonApprovalRecordRepository
from infrastructure.json_implementation_evidence_repository import JsonImplementationEvidenceRepository


pages = Blueprint('human_workflows', __name__,
    url_prefix='/control/projects/<project_id>/workflows/<workflow_id>')

POINTS = {
    'PLAN_APPROVAL': '計画の確認・承認を待っています。',
    'REVIEW_INPUT': 'レビューに渡す材料を確認できています。',
    'REVIEW_HANDOFF': 'レビュー後の引き継ぎ内容を確認できています。',
    'FINAL_APPROVAL': '最終確認・承認を待っています。',
    'HUMAN_HANDOFF': '以前のHuman判断による返却内容を確認してください。',
}


class MissingApprovals:
    def get(self, identity):
        raise ValueError('正式Approvalの保存先が未設定です。SPECFLOW_APPROVALS_DIRを明示してください。')


def continuity(repository, approvals_dir=None, evidence_dir=None):
    # Explicit composition only; never discover a store from names / path guesses.
    approvals = JsonApprovalRecordRepository(Path(approvals_dir)) if approvals_dir else MissingApprovals()
    evidence = JsonImplementationEvidenceRepository(Path(evidence_dir)) if evidence_dir else None
    # T5 calls only the existing read-only _validate_target helper. No execution ports.
    final = FinalApprovalWorkflowUseCase(None, approvals, evidence, None)
    resume = ResumeService(WorkflowService(repository), approvals,
        final_workflow=final, evidence_repository=evidence)
    return EndWorkService(repository, resume)


def stopped(message, status):
    return render_template('project_problem.html', message=message), status


def context(project_id, workflow_id):
    runtime = current_app.extensions['human_control']
    p, w = runtime.target(project_id, workflow_id)
    repo = runtime.require_repository()
    service = current_app.extensions['human_continuity']
    observation = runtime.outputs.get(p, w)
    result = service.resume(p, w, observation=observation)
    project, work = repo.get_project(p), repo.get_workflow(w)
    active = ProjectService(repo).active_project()
    intent = repo.human_intent(p, w)
    # Fresh T5 result + actual index / Intent / Focus, never posted hidden state.
    stamp = hashlib.sha256(json.dumps([asdict(project), asdict(work),
        repo.artifact_references(w), intent, asdict(active) if active else None,
        asdict(result)], default=str, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return dict(runtime=runtime, service=service, project=project, work=work,
        result=result, observation=observation, intent=intent, stamp=stamp,
        active=active is not None and active.project_id == p)


def render_screen(project_id, workflow_id, ending=False):
    try:
        data = context(project_id, workflow_id)
        attempt = current_app.extensions['human_decisions'].get(data['work'].workflow_id)
        data['decision_attempt'] = attempt if attempt and attempt.project_id == data['project'].project_id else None
        actions = ['intent', 'delete-intent', 'end-work']
        if ending and data['active']:
            actions += ['keep-active', 'sleep']
        tokens = {action: data['runtime'].forms.issue('workflow:' + action,
            data['project'].project_id, data['work'].workflow_id, revision=data['stamp'])
            for action in actions}
        projection = data['result'].projection
        point = POINTS.get(projection.resume_point) if projection and projection.reconstructed else None
        return render_template('human_workflow.html', **data, tokens=tokens,
            ending=ending, projection=projection, point=point)
    except BoundaryError:
        return stopped('対象のProject / Workflowが存在しないか、所属が一致しません。', 404)
    except Exception:
        return stopped('対象情報を取得できません。成功とは扱わず操作を停止しました。', 503)


@pages.get('')
def detail(project_id, workflow_id):
    return render_screen(project_id, workflow_id)


@pages.get('/end-work')
def end_screen(project_id, workflow_id):
    # Viewing this page does not call end(), persist a session, or change Focus.
    return render_screen(project_id, workflow_id, ending=True)


@pages.post('/<action>')
def change(project_id, workflow_id, action):
    if action not in ('intent', 'delete-intent', 'end-work', 'keep-active', 'sleep'):
        return stopped('指定された操作はありません。', 404)
    try:
        data = context(project_id, workflow_id)
    except BoundaryError:
        return stopped('対象のProject / Workflowが存在しないか、所属が一致しません。', 404)
    except Exception:
        return stopped('対象情報を確認できません。変更せず操作を停止しました。', 503)
    p, w = data['project'].project_id, data['work'].workflow_id
    try:
        data['runtime'].forms.consume(request.form.get('token'), 'workflow:' + action,
            p, w, revision=data['stamp'])
    except BoundaryError:
        return stopped('対象不一致・再送または表示後の変更を検出しました。画面を再表示してください。', 409)
    if request.form.get('human_confirmed') != 'yes':
        return stopped('Humanの明示確認が必要です。', 400)
    service = data['service']
    try:
        if action == 'intent':
            service.repository.save_human_intent(p, w, request.form.get('intent', ''))
            flash('次に考えていたことを確認しました。空欄の場合は変更していません。')
        else:
            if action == 'delete-intent':
                result = service.delete_intent(p, w, human_confirmed=True)
            elif action == 'end-work':
                result = service.end(p, w, operation_returned=True, observation=data['observation'])
            else:
                if not data['active']:
                    return stopped('進行中のProjectにのみ使える操作です。明示ActivateはProject画面で行ってください。', 409)
                result = service.choose_focus(p, w,
                    choice='keep_active' if action == 'keep-active' else 'sleep', human_confirmed=True)
            if not result.success:
                return stopped('操作結果を確認できません。再表示して保存内容を確認してください。'
                    + (' Intentは保存済みです。' if result.intent_saved else ''), 503)
            flash({'delete-intent': '過去のHuman Intentを削除しました。',
                'end-work': '今日はここまで。作業を終了しました。再開可否は以下の正式情報の確認結果をご覧ください。',
                'keep-active': '進行中のままにしました。',
                'sleep': '寝かせました。今回の明示操作の日時を記録しました。'}[action])
    except Exception:
        return stopped('保存結果を確認できません。成功とは扱わず、再表示して確認してください。', 503)
    ending = action in ('end-work', 'keep-active', 'sleep') or request.form.get('return_to') == 'end-work'
    return redirect(url_for('human_workflows.end_screen' if ending else 'human_workflows.detail',
        project_id=p, workflow_id=w), code=303)
