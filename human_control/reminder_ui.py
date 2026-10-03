"""T7 presentation: Human direct registration and explicit association removal."""
from dataclasses import asdict
import hashlib
import json

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from human_control.models import REMINDER_KINDS, require_text
from human_control.reminders import ReminderService
from human_control.web_runtime import BoundaryError, parse_uuid


pages = Blueprint('human_reminders', __name__)
PROVENANCE = {'human_direct': 'Humanが直接残したもの',
              'ai_proposed_human_saved': 'AI提案をHumanが残すと決めたもの'}


def stopped(message, status=503):
    return render_template('project_problem.html', message=message), status


def dependencies():
    runtime = current_app.extensions['human_control']
    return runtime, ReminderService(runtime.require_repository())


def project_context(runtime, project_id):
    p, _ = runtime.target(project_id)
    repo = runtime.require_repository()
    return repo.get_project(p), repo.list_workflows(p)


def revision(project, works, item=None):
    # Display context only. Targets / ownership are independently re-read on POST.
    data = [asdict(project), [asdict(w) for w in works], asdict(item) if item else None]
    return hashlib.sha256(json.dumps(data, default=str, sort_keys=True,
                                   ensure_ascii=False).encode()).hexdigest()


def workflow_parameter(runtime, project_id, values):
    selected = values.getlist('workflow_id')
    if len(selected) > 1:
        raise BoundaryError('One Workflow is required')
    value = selected[0] if selected else ''
    return runtime.target(project_id, value)[1] if value else None


def group(runtime, service, project, workflow_id=None):
    result = service.list_for_project(project.project_id)
    if not result.success:
        raise RuntimeError('Reminder read failed')
    works = service.repository.list_workflows(project.project_id)
    names = {work.workflow_id: work.name for work in works}
    rows = []
    for item in result.reminders:
        if item.project_id != project.project_id:
            raise BoundaryError('Reminder ownership mismatch')
        if item.workflow_id is not None:
            runtime.target(project.project_id, item.workflow_id)
        if workflow_id is not None and item.workflow_id != workflow_id:
            continue
        action = 'reminder:detach:' + str(item.reminder_id)
        token = (runtime.forms.issue(action, project.project_id, item.workflow_id,
                    revision=revision(project, works, item)) if item.workflow_id is not None else None)
        rows.append(dict(item=item, workflow_name=names.get(item.workflow_id), token=token))
    return dict(project=project, rows=rows)


@pages.get('/control/reminders')
def all_reminders():
    try:
        runtime, service = dependencies()
        repo = service.repository
        active = repo.active_project()
        projects = ((active,) if active else ()) + repo.sleeping_projects()
        groups = [group(runtime, service, project) for project in projects]
        return render_template('reminders.html', groups=groups, selected=None,
                               workflow=None, provenance=PROVENANCE)
    except Exception:
        return stopped('Reminder一覧を取得できません。空の一覧とは判断せず停止しました。')


@pages.get('/control/projects/<project_id>/reminders')
def project_reminders(project_id):
    try:
        runtime, service = dependencies()
        project, works = project_context(runtime, project_id)
        w = workflow_parameter(runtime, project.project_id, request.args)
        workflow = next((work for work in works if work.workflow_id == w), None)
        return render_template('reminders.html', groups=[group(runtime, service, project, w)],
                               selected=project, workflow=workflow, provenance=PROVENANCE)
    except (BoundaryError, KeyError):
        return stopped('Project / WorkflowのUUIDまたは所属を確認できません。', 404)
    except Exception:
        return stopped('Reminder一覧を取得できません。空の一覧とは判断せず停止しました。')


@pages.route('/control/projects/<project_id>/reminders/new', methods=['GET', 'POST'])
def new(project_id):
    try:
        runtime, service = dependencies()
        project, works = project_context(runtime, project_id)
        stamp = revision(project, works)
        if request.method == 'GET':
            w = workflow_parameter(runtime, project.project_id, request.args)
            candidate = next((work for work in works if work.workflow_id == w), None)
            token = runtime.forms.issue('reminder:create', project.project_id, revision=stamp)
            return render_template('reminder_new.html', project=project, works=works,
                                   candidate=candidate, token=token, kinds=REMINDER_KINDS)
    except (BoundaryError, KeyError):
        return stopped('Project / WorkflowのUUIDまたは所属を確認できません。', 404)
    except Exception:
        return stopped('登録対象を取得できません。操作を停止しました。')
    try:
        runtime.forms.consume(request.form.get('token'), 'reminder:create', project.project_id,
                              revision=stamp)
    except BoundaryError:
        return stopped('対象不一致・再送または表示後の変更です。登録画面を再表示してください。', 409)
    if request.form.get('human_confirmed') != 'yes':
        return stopped('Humanが残しておくと決めた明示確認が必要です。', 400)
    kinds = request.form.getlist('kind')
    try:
        text = require_text(request.form.get('text', ''))
        if len(kinds) != 1 or kinds[0] not in REMINDER_KINDS:
            raise ValueError('One explicit kind required')
    except (TypeError, ValueError):
        return stopped('内容を入力し、既存の5種類から1つ選択してください。', 400)
    try:
        w = workflow_parameter(runtime, project.project_id, request.form)
    except (BoundaryError, KeyError):
        return stopped('指定されたWorkflowのUUIDまたはProjectとの所属が一致しません。', 404)
    except Exception:
        return stopped('Workflowの所属を確認できません。登録を停止しました。')
    if w is not None and request.form.get('confirm_workflow') != 'yes':
        return stopped('Workflowとの関連付けにはHumanの明示確認が必要です。', 400)
    result = service.register(project.project_id, text, kinds[0], human_confirmed=True,
                              workflow_id=w, location=request.form.get('location'))
    if not result.success:
        return stopped('保存結果を確認できません。成功とは扱わず、一覧を確認してから操作してください。')
    flash('思い出しておくことを残しました。実行や優先順位の決定ではありません。')
    return redirect(url_for('human_reminders.project_reminders', project_id=project.project_id), code=303)


@pages.post('/control/projects/<project_id>/reminders/<reminder_id>/detach')
def detach(project_id, reminder_id):
    try:
        runtime, service = dependencies()
        project, works = project_context(runtime, project_id)
        identity = parse_uuid(reminder_id)
        item = service.repository.get_reminder(project.project_id, identity)
        if item.workflow_id is not None:
            runtime.target(project.project_id, item.workflow_id)
    except (BoundaryError, KeyError):
        return stopped('Reminder / Project / WorkflowのUUIDまたは所属が一致しません。', 404)
    except Exception:
        return stopped('関連付けの現在情報を取得できません。操作を停止しました。')
    try:
        runtime.forms.consume(request.form.get('token'), 'reminder:detach:' + str(identity),
            project.project_id, item.workflow_id, revision=revision(project, works, item))
    except BoundaryError:
        return stopped('対象不一致・再送または表示後の変更です。一覧を再表示してください。', 409)
    if request.form.get('human_confirmed') != 'yes':
        return stopped('関連を解除するHumanの明示確認が必要です。', 400)
    if item.workflow_id is None:
        return stopped('このReminderにはWorkflowの関連がありません。', 409)
    result = service.unlink_workflow(project.project_id, identity, human_confirmed=True)
    if not result.success:
        return stopped('解除結果を確認できません。成功とは扱わず、一覧を再表示してください。')
    flash('Workflowとの関連だけを解除しました。Reminderの内容・Project・由来は保持しています。')
    return redirect(url_for('human_reminders.project_reminders', project_id=project.project_id), code=303)
