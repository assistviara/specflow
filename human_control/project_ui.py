"""HTML input adapters for ProjectService; no Workflow execution or Artifact IO."""
import hashlib
import json
from uuid import uuid4

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for

from human_control.projects import ProjectService
from human_control.web_runtime import BoundaryError
from human_control.focus_ui import focus_controls


pages = Blueprint('human_projects', __name__, url_prefix='/control/projects')
FIELDS = {'purpose': '目的', 'values': '大切にすること', 'rules': '守ること'}


def dependencies():
    runtime = current_app.extensions['human_control']
    return runtime, ProjectService(runtime.require_repository())


def problem(message, status):
    return render_template('project_problem.html', message=message), status


def revision(items):
    # Only freshly read server data supplies the current revision, never form hashes.
    content = {key: [item.value, item.confirmed] for key, item in items.items()}
    return hashlib.sha256(json.dumps(content, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def handoff(change):
    if change.human_review_required:
        names = '、'.join(f'{work.name}（{work.workflow_id}）' for work in change.workflows)
        flash('基本方針の変更について人による判断が必要です。対象の仕事：' + names +
              '。変更後の基本方針と正式な記録を確認し、継続・停止・再検討を判断してください。'
              '状態不明は完了とみなしていません。自動停止・自動継続・正式状態の変更は行っていません。'
              '各項目の再確認だけでは、進行中の仕事への影響判断済みにはなりません。')


@pages.route('/new', methods=['GET', 'POST'])
def new():
    runtime, service = dependencies()
    if request.method == 'GET':
        # Form identity only. ProjectService independently issues the Project UUID.
        draft = session.setdefault('project_draft', str(uuid4()))
        token = runtime.forms.issue('create-project', draft, revision=draft)
        return render_template('project_new.html', fields=FIELDS, draft_id=draft, token=token)
    draft = session.get('project_draft')
    try:
        if not draft or request.form.get('draft_id') != draft:
            raise BoundaryError('作成画面の対象が一致しません。')
        runtime.forms.consume(request.form.get('token'), 'create-project', draft, revision=draft)
    except BoundaryError:
        return problem('作成画面が古いか、対象不一致・再送です。新しい作成画面を開いてください。', 409)
    name = request.form.get('name', '')
    mode = request.form.get('mode')
    reference = request.form.get('reference', '')
    if not name.strip() or mode not in ('new', 'existing'):
        return problem('プロジェクト名と作成方法を指定してください。', 400)
    if mode == 'existing' and (not reference.strip() or request.form.get('register_confirmed') != 'yes'):
        return problem('既存開発物の参照と、これから管理するという明示確認が必要です。', 400)
    try:
        project = (service.create(name) if mode == 'new' else
                   service.register_existing(name, reference, human_confirmed=True))
    except Exception:
        return problem('プロジェクトの作成結果を確認できません。保存先を確認してください。自動再作成はしません。', 503)
    flash('プロジェクトは作成済みです。')
    # Independent service transactions: never claim all-or-nothing persistence.
    for field, label in FIELDS.items():
        value = request.form.get(field, '')
        try:
            service.update_constitution(project.project_id, field, value)
        except Exception:
            flash(f'{label}の保存処理に失敗しました。未保存の入力や未確認の項目は下の現在値を確認して再入力してください。以降の項目は処理していません。')
            break
        if value.strip() and request.form.get('confirm_' + field) == 'yes':
            try:
                service.confirm_constitution(project.project_id, field, value, human_confirmed=True)
            except Exception:
                flash(f'{label}は保存済みですが、確認処理に失敗しました。現在の確認状態を確認してください。以降の項目は処理していません。')
                break
    return redirect(url_for('human_projects.detail', project_id=project.project_id), code=303)


@pages.get('/<project_id>')
def detail(project_id):
    runtime, service = dependencies()
    try:
        identity, _ = runtime.target(project_id)
    except BoundaryError:
        return problem('指定されたプロジェクトが見つかりません。UUIDを確認してください。', 404)
    except Exception:
        return problem('保存先から対象を確認できません。操作を停止しました。', 503)
    try:
        project = service.repository.get_project(identity)
        items = service.constitution(identity)
        gate = service.workflow_start_gate(identity)
        active = service.active_project()
        reference = service.repository.existing_project_reference(identity)
        stamp = revision(items)
        tokens = {field: {action: runtime.forms.issue(f'{action}:{field}', identity, revision=stamp)
                          for action in ('edit', 'confirm')} for field in FIELDS}
        return render_template('human_project.html', project=project, fields=FIELDS, items=items,
            gate=gate, active=active is not None and active.project_id == identity,
            reference=reference, tokens=tokens, focus=focus_controls(runtime, project, active),
            workflows=service.repository.list_workflows(identity))
    except Exception:
        return problem('保存済み情報を取得できません。変更せずに操作を停止しました。', 503)


@pages.post('/<project_id>/constitution/<field>/<action>')
def constitution(project_id, field, action):
    runtime, service = dependencies()
    if field not in FIELDS or action not in ('edit', 'confirm'):
        return problem('指定された操作はありません。', 404)
    try:
        identity, _ = runtime.target(project_id)
    except BoundaryError:
        return problem('指定されたプロジェクトが見つかりません。', 404)
    except Exception:
        return problem('保存先から対象を確認できません。操作を停止しました。', 503)
    try:
        items = service.constitution(identity)
        runtime.forms.consume(request.form.get('token'), f'{action}:{field}', identity,
                              revision=revision(items))
    except BoundaryError:
        return problem('対象不一致・再送、または内容が変更されています。プロジェクト画面を再表示してください。', 409)
    except Exception:
        return problem('現在の保存内容を確認できないため、操作を停止しました。', 503)
    if action == 'confirm':
        if request.form.get('human_confirmed') != 'yes':
            return problem('内容について人による明示確認が必要です。', 400)
        if request.form.get('expected_value') != items[field].value:
            return problem('確認対象の内容が一致しません。現在の内容を確認してください。', 409)
        try:
            service.confirm_constitution(identity, field, request.form.get('expected_value'),
                                         human_confirmed=True)
            flash(FIELDS[field] + 'を明示確認しました。')
        except ValueError:
            return problem('空欄または変更された内容は確認できません。再表示してください。', 409)
        except Exception:
            flash('確認処理に失敗しました。現在の確認状態を確認してください。')
    else:
        try:
            change = service.update_constitution(identity, field, request.form.get('value', ''))
            flash(FIELDS[field] + 'を保存しました。変更した内容は明示確認が必要です。')
            handoff(change)
        except Exception:
            flash('保存処理に失敗しました。保存が一部成立している可能性もあるため、現在値と確認状態を確認してください。')
    return redirect(url_for('human_projects.detail', project_id=identity), code=303)
