"""Project focus presentation and explicit POSTs; no Workflow execution."""
import json

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from human_control.projects import ProjectService
from human_control.web_runtime import BoundaryError


pages = Blueprint('human_focus', __name__)


def focus_revision(project, active):
    """Bind what Human saw: target and current Active, including displayed names.

    This is form context, not a persisted State or execution authorization.
    The caller always supplies fresh repository reads at POST time.
    """
    return json.dumps([str(project.project_id), project.name,
        [str(active.project_id), active.name] if active is not None else None], ensure_ascii=False)


def focus_controls(runtime, project, active):
    action = 'sleep' if active is not None and active.project_id == project.project_id else 'activate'
    return dict(project=project, action=action, previous=active,
        token=runtime.forms.issue('focus:' + action, project.project_id,
                                  revision=focus_revision(project, active)))


def services():
    runtime = current_app.extensions['human_control']
    return runtime, ProjectService(runtime.require_repository())


def stopped(message, status=503):
    return render_template('project_problem.html', message=message), status


@pages.get('/')
def home():
    try:
        _, service = services()
        return render_template('home.html', active=service.active_project(),
                               recent=service.recent_sleeping())
    except Exception:
        return stopped('プロジェクト情報を取得できません。空の一覧とは判断せず、操作を停止しました。')


@pages.get('/control/projects/sleeping')
def sleeping():
    try:
        runtime, service = services()
        active = service.active_project()
        projects = service.sleeping_projects()
        controls = {p.project_id: focus_controls(runtime, p, active) for p in projects}
        return render_template('sleeping_projects.html', projects=projects, controls=controls)
    except Exception:
        return stopped('寝かせたプロジェクトを取得できません。空の一覧とは判断せず、操作を停止しました。')


@pages.post('/control/projects/<project_id>/focus/<action>')
def change(project_id, action):
    if action not in ('activate', 'sleep'):
        return stopped('指定された操作はありません。', 404)
    try:
        runtime, service = services()
        identity, _ = runtime.target(project_id)
        project = service.repository.get_project(identity)
        active = service.active_project()
    except BoundaryError:
        return stopped('指定されたプロジェクトが見つかりません。', 404)
    except Exception:
        return stopped('現在の対象と作業対象を確認できません。変更せず操作を停止しました。')
    try:
        runtime.forms.consume(request.form.get('token'), 'focus:' + action, identity,
                              revision=focus_revision(project, active))
    except BoundaryError:
        return stopped('対象不一致・再送、または作業対象が変更されています。画面を再表示してください。', 409)
    if request.form.get('human_confirmed') != 'yes':
        return stopped('作業対象を変更する明示確認が必要です。', 400)
    is_active = active is not None and active.project_id == identity
    if (action == 'sleep' and not is_active) or (action == 'activate' and is_active):
        return stopped('現在の作業対象と操作が一致しません。画面を再表示してください。', 409)
    try:
        # Existing service owns transactions and explicit Sleep timestamps.
        # No posted name, timestamp or other hidden data supplies authority.
        if action == 'activate':
            service.activate(identity, human_confirmed=True)
        else:
            service.sleep(identity, human_confirmed=True)
    except Exception:
        return stopped('作業対象の変更結果を確認できません。成功とは扱わず停止しました。ホームで現在の状態を確認してください。')
    if action == 'activate':
        flash(f'「{project.name}」を進行中にしました。')
        if active is not None:
            flash(f'以前の作業対象「{active.name}」を寝かせました。この切替を新しい明示的な「寝かせる」日時としては記録していません。')
    else:
        flash(f'「{project.name}」を寝かせました。今回の明示操作の日時を記録しました。')
    return redirect(url_for('human_projects.detail', project_id=identity), code=303)
