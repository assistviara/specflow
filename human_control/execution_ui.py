"""Synchronous HTML connection to T4. No persistent execution checkpoint.

create_app(execution_factory=...) accepts an explicit composition callable:
factory(workflows, registered_workflow) -> ApplicationPorts. It must supply the
real Phase 7 services and their configured AI, execution, storage and retry ports.
No executable defaults, model selection, mock fallback or retry authorization.
"""
from dataclasses import dataclass
import hashlib
import json
from threading import RLock
from uuid import uuid4

from flask import Blueprint, current_app, redirect, render_template, request, url_for

from application.dto import (GenerateImplementationPlanInput, RequestPlanApprovalInput,
    ReviseImplementationPlanInput, GenerateCodexPromptInput)
from application.plan_workflow import PlanWorkflowOutput
from application.implementation_workflow import ImplementationWorkflowInput, InitialTddApplicability
from application.implementation_evidence import EvidenceScope
from human_control.application_adapter import ApplicationAdapter, ApplicationPorts, DelegatedInputs
from human_control.projects import ProjectService
from human_control.project_ui import problem, revision
from human_control.web_runtime import BoundaryError
from human_control.workflows import WorkflowService, explicit_path
from human_control.workflow_preparation import configured, new_decision_identity

pages = Blueprint('human_execution', __name__, url_prefix='/control/projects/<project_id>/workflows')
START_FILES = ('specification', 'state', 'constitution', 'principles', 'decisions',
               'plan_template', 'plan_prompt_template')
START_PATHS = (*START_FILES, 'history', 'plan')
METADATA = ('project_name', 'target_path', 'project_description', 'project_version')
START_FIELDS = ('name', 'approval_id', *START_PATHS, *METADATA)
LABELS = dict(name='作業名', approval_id='保存済みSpecification Approval ID',
    specification='正式Specification', state='既存Stateファイル', history='History保存先',
    constitution='正式Constitution文書', principles='正式Principles文書', decisions='正式Decisions文書',
    plan_template='Plan文書テンプレート', plan_prompt_template='Plan生成Promptテンプレート',
    plan='新しいPlan保存先（未使用）', project_name='正式Project名（生成入力）',
    target_path='正式target_path（生成入力）', project_description='正式Project説明', project_version='正式Project版')
DELEGATED_LABELS = dict(repository='対象Repositoryの絶対パス', implementation_target='実装対象の絶対パス',
    implementation_branch='実装branch', prompt_template='Implementation Promptテンプレートの絶対パス',
    codex_prompt='Prompt保存先の絶対パス（未使用）', review_dir='Review保存先の絶対パス',
    final_dir='Final保存先の絶対パス', tdd_rules='TDD規則', completion_conditions='完了条件',
    stop_conditions='停止条件', execution_result_reporting_requirements='結果報告要件',
    target_paths='承認対象path（JSON文字列配列）', allowed_changes='許可する変更（JSON文字列配列）',
    forbidden_changes='禁止する変更（JSON文字列配列）', source_paths='source絶対path（JSON文字列配列）',
    test_paths='test絶対path（JSON文字列配列）')


@dataclass
class Run:
    adapter: ApplicationAdapter | None = None
    result: object = None
    stamp: str | None = None
    failure: str = ''


class ExecutionRuntime:
    def __init__(self, factory=None):
        self.factory = factory
        self.runs = {}
        # Serialize this process's synchronous mutations; no workers / queue.
        self.lock = RLock()


def dependencies(project_id, workflow_id=None):
    runtime = current_app.extensions['human_control']
    p, w = runtime.target(project_id, workflow_id)
    return runtime, current_app.extensions['human_execution'], WorkflowService(runtime.require_repository()), p, w


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def file_fact(path):
    if path.is_file():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    return 'directory' if path.is_dir() else 'missing'


def approvals():
    return current_app.extensions['human_continuity'].projection_service.approvals


def approval_fact(identity):
    # Only the supplied ID is read. Missing records remain Phase 7 validation input.
    if (not isinstance(identity, str) or not identity.strip() or identity in ('.', '..')
            or any(c in identity for c in '/\\:*?')):
        raise ValueError('Approval IDには単一の保存済みIDを指定してください。')
    try:
        return approvals().get(identity)
    except FileNotFoundError:
        return None


def snapshot(paths, approval_id):
    facts = {role: (str(path), file_fact(path)) for role, path in paths.items()}
    history = paths['history']
    if history.is_dir():
        facts['history_files'] = [(str(p.relative_to(history)), file_fact(p))
                                  for p in sorted(history.rglob('*')) if p.is_file()]
    facts['specification_approval'] = approval_fact(approval_id)
    return facts


def project_stamp(service, p):
    return revision(ProjectService(service.repository).constitution(p))


def required(form, key):
    value = form.get(key, '')
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'明示入力が必要です: {key}')
    return value


def selected_start(service, p, execution):
    if not callable(execution.factory):
        raise ValueError('実行用Application Layer依存が未設定です。STOP / Human Handoff。')
    if not ProjectService(service.repository).workflow_start_gate(p).allowed:
        raise ValueError('基本方針3項目の明示確認が必要です。')
    values = {key: required(request.form, key) for key in START_FIELDS}
    paths = {key: explicit_path(values[key]) for key in START_PATHS}
    for key in START_FILES:
        if not paths[key].is_file():
            raise ValueError(f'正式入力ファイルがありません: {key}')
    if paths['plan'].exists():
        raise ValueError('Planには未使用の保存先を指定してください。')
    if paths['history'].exists() and not paths['history'].is_dir():
        raise ValueError('History保存先がdirectoryではありません。')
    stamp = digest((values, project_stamp(service, p), snapshot(paths, values['approval_id'])))
    return values, paths, stamp


@pages.route('/new', methods=['GET', 'POST'])
def new(project_id):
    try:
        runtime, execution, service, p, _ = dependencies(project_id)
        preparation = configured()
        if preparation is not None:
            with execution.lock:
                return preparation.page(runtime, service, p)
        if request.method == 'GET':
            token = runtime.forms.issue('execution:prepare', p, revision=project_stamp(service, p))
            return render_template('workflow_start.html', p=p, token=token, fields=LABELS, values=None)
        with execution.lock:
            runtime.forms.consume(request.form.get('token'), 'execution:prepare', p,
                                  revision=project_stamp(service, p))
            values, paths, stamp = selected_start(service, p, execution)
            token = runtime.forms.issue('execution:start', p, revision=stamp)
            return render_template('workflow_start.html', p=p, token=token, fields=LABELS,
                                   values=values, spec_hash=file_fact(paths['specification']))
    except BoundaryError:
        return problem('対象不一致・古い画面・再送です。再表示してください。', 409)
    except ValueError as exc:
        return problem(str(exc), 400)
    except Exception:
        return problem('STOP: 正式入力または保存先を確認できません。', 503)


@pages.post('/approve-specification')
def approve_specification(project_id):
    try:
        runtime, execution, service, p, _ = dependencies(project_id)
        with execution.lock:
            preparation = configured()
            if preparation is None or not callable(execution.factory):
                raise ValueError('正式入力準備・実行依存が未設定です。')
            return preparation.approve(runtime, service, p, approvals())
    except (ValueError, OSError) as exc:
        return problem('STOP: ' + str(exc), 409)
    except Exception:
        return problem('STOP: 承認の保存結果を確認できません。自動再実行しません。', 503)


def location(p, w):
    return url_for('human_execution.detail', project_id=p, workflow_id=w)


def run_stamp(service, p, w, run):
    work, paths = service.binding(p, w)
    records = [approval_fact(output.approval_result.approval_record['approval_id'])
        for output in run.adapter.observation().outputs
        if isinstance(output, PlanWorkflowOutput) and output.approval_result is not None]
    return digest((work, paths, snapshot(paths, work.approval_id), run.adapter.observation(),
                   records, project_stamp(service, p)))


def retain(runtime, service, p, w, run):
    if run.adapter is not None:
        try:
            runtime.outputs.put(run.adapter.observation())
            run.stamp = run_stamp(service, p, w, run)
        except Exception:
            run.failure = '実Outputの格納または正式Artifact / indexの再確認に失敗しました。STOP。実adapterと保存済み情報を保持しています。'


@pages.post('/start')
def start(project_id):
    try:
        runtime, execution, service, p, _ = dependencies(project_id)
        with execution.lock:
            preparation = configured()
            if preparation is not None:
                if not callable(execution.factory):
                    raise ValueError('実行依存が未設定です。')
                values, paths = preparation.begin(runtime, service, p, approvals())
            else:
                values, paths, stamp = selected_start(service, p, execution)
                runtime.forms.consume(request.form.get('token'), 'execution:start', p, revision=stamp)
                if request.form.get('human_confirmed') != 'yes':
                    raise ValueError('新しいWorkflowの開始には人による明示確認が必要です。')
            refs = {role: path for role, path in paths.items() if role not in ('specification', 'state', 'history')}
            work = service.register(p, values['name'], paths['specification'], file_fact(paths['specification']),
                values['approval_id'], paths['state'], paths['history'], refs, human_confirmed=True)
            run = execution.runs[work.workflow_id] = Run()
            try:
                ports = execution.factory(service, work)
                if not isinstance(ports, ApplicationPorts):
                    raise ValueError('ApplicationPorts required')
                for port, methods in ((ports.entry, ('execute',)),
                        (ports.plans, ('generate', 'decide', 'revise', 'generate_prompt')),
                        (ports.implementation, ('execute',)), (ports.evidence, ('execute',)),
                        (ports.review, ('start',)), (ports.final, ('start',))):
                    if any(not callable(getattr(port, method, None)) for method in methods):
                        raise ValueError('Required Application Layer dependency missing')
                run.adapter = ApplicationAdapter(service, p, work.workflow_id, ports)
                generation = GenerateImplementationPlanInput(paths['constitution'], paths['principles'],
                    paths['specification'], {}, paths['decisions'], paths['plan_template'],
                    {k: values[k] for k in METADATA}, paths['plan_prompt_template'], paths['state'], paths['history'])
                run.result = run.adapter.start(generation)
            except Exception:
                run.failure = '実行用依存の取得または実行に失敗しました。STOP。自動再実行はしません。'
            retain(runtime, service, p, work.workflow_id, run)
            return redirect(location(p, work.workflow_id), code=303)
    except BoundaryError:
        return problem('対象不一致・古い画面・再送です。開始していません。', 409)
    except ValueError as exc:
        # A consumed start token must never authorize a retry, including partial failures.
        return problem('STOP: ' + str(exc), 409)
    except Exception:
        return problem('STOP: 登録・保存結果を確認できません。Projectの登録済みWorkflowを確認してください。自動再作成しません。', 503)


def active_plan(service, p, w, run):
    if (run is None or run.adapter is None or run.failure or run.result is None or not run.result.success
            or run.stamp != run_stamp(service, p, w, run)):
        raise BoundaryError('STOP: process内の実行結果がないか、正式入力が変更されています。正式記録を確認してください。')
    outputs = run.adapter.observation().outputs
    # Only the last actual Output authorizes this UI's Plan interaction.
    plan = outputs[-1] if outputs else None
    if not isinstance(plan, PlanWorkflowOutput) or not plan.success or plan.prompt_result is not None:
        raise BoundaryError('STOP: Plan判断の対象ではありません。実際のOutputを確認してください。')
    draft = plan.draft_result
    content = getattr(draft, 'implementation_plan_draft', None)
    if content is None:
        content = getattr(draft, 'revised_implementation_plan_draft', None)
    if not isinstance(content, str) or plan.plan_path.read_bytes() != content.encode('utf-8'):
        raise BoundaryError('STOP: 保存済みPlanと生成結果が一致しません。')
    return plan, content


@pages.get('/<workflow_id>/execution')
def detail(project_id, workflow_id):
    try:
        runtime, execution, service, p, w = dependencies(project_id, workflow_id)
        work = service.repository.get_workflow(w)
        run = execution.runs.get(w)
        content, token, action, message = None, None, None, ''
        try:
            if (run is not None and run.adapter is not None and run.result is not None
                    and run.result.success and not run.failure
                    and run.stamp == run_stamp(service, p, w, run)
                    and not isinstance(run.adapter.observation().outputs[-1], PlanWorkflowOutput)):
                return render_template('workflow_execution.html', p=p, w=w, work=work, run=run,
                    content=None, token=None, action=None,
                    message='人の確認・判断を待っています。保持された結果と正式記録を確認してください。',
                    delegated=DELEGATED_LABELS)
            plan, content = active_plan(service, p, w, run)
            choice = plan.approval_result.decision if plan.approval_result else None
            if choice is None:
                action, message = 'decide', '計画の判断を待っています'
            elif choice == 'revision_requested':
                action, message = 'revise', '修正要求を受け付けました。修正入力を確認してください。'
            else:
                message = '人による中止判断を受け付けました。'
            if action:
                token = runtime.forms.issue('execution:' + action, p, w, revision=run.stamp)
        except (BoundaryError, ValueError, OSError) as exc:
            message = str(exc)
        return render_template('workflow_execution.html', p=p, w=w, work=work, run=run,
            content=content, token=token, action=action, message=message, delegated=DELEGATED_LABELS)
    except BoundaryError:
        return problem('Project / Workflow UUIDまたはownershipが一致しません。', 404)
    except Exception:
        return problem('STOP: 保存済み情報を読み取れません。', 503)


def array_input(key, form=None):
    value = json.loads(required(request.form if form is None else form, key))
    if not isinstance(value, list) or any(not isinstance(v, str) or not v.strip() for v in value):
        raise ValueError(f'文字列のJSON配列が必要です: {key}')
    return tuple(value)


def delegated_inputs(work, paths, approval_id):
    preparation = configured()
    form = preparation.delegated_form(work, paths, request.form) if preparation is not None else request.form
    refs = {key: explicit_path(required(form, key)) for key in
            ('repository', 'implementation_target', 'prompt_template', 'codex_prompt', 'review_dir', 'final_dir')}
    if not refs['repository'].is_dir() or not refs['prompt_template'].is_file():
        raise ValueError('Repositoryと正式Promptテンプレートが必要です。')
    if refs['codex_prompt'].exists():
        raise ValueError('Prompt保存先は未使用である必要があります。')
    for key in ('review_dir', 'final_dir'):
        if refs[key].exists() and not refs[key].is_dir():
            raise ValueError('Review / Final保存先にはdirectoryを指定してください。')
    texts = {key: required(form, key) for key in ('tdd_rules', 'completion_conditions',
        'stop_conditions', 'execution_result_reporting_requirements', 'implementation_branch', 'review_mode', 'tdd_required')}
    if texts['review_mode'] not in ('BATCH', 'STAGED') or texts['tdd_required'] not in ('yes', 'no'):
        raise ValueError('Review方式とTDD適用の明示選択が必要です。')
    no_tdd_reason = required(form, 'no_tdd_reason') if texts['tdd_required'] == 'no' else None
    scope = EvidenceScope(array_input('target_paths', form), array_input('allowed_changes', form), array_input('forbidden_changes', form))
    source, tests = [tuple(explicit_path(v) for v in array_input(key, form)) for key in ('source_paths', 'test_paths')]
    if any(not path.is_relative_to(refs['repository']) for path in (*source, *tests)):
        raise ValueError('source / testは対象Repository内の明示pathが必要です。')
    prompt = GenerateCodexPromptInput(paths['specification'], work.approval_id, paths['plan'], approval_id,
        refs['implementation_target'], texts['tdd_rules'], texts['completion_conditions'], texts['stop_conditions'],
        texts['execution_result_reporting_requirements'], refs['prompt_template'], paths['state'], paths['history'])

    def implementation(actual):
        record = actual.approval_result.approval_record
        return ImplementationWorkflowInput(actual, uuid4(), refs['repository'], texts['implementation_branch'],
            InitialTddApplicability(actual.plan_path, record['approval_id'], record['artifact_hash'],
                hashlib.sha256(actual.prompt_result.codex_prompt.encode('utf-8')).hexdigest(),
                texts['tdd_required'] == 'yes', no_tdd_reason))
    return refs, DelegatedInputs(prompt, implementation, scope, source, tests, texts['review_mode'])


@pages.post('/<workflow_id>/execution/<action>')
def act(project_id, workflow_id, action):
    if action not in ('decide', 'revise'):
        return problem('指定された操作はありません。', 404)
    try:
        runtime, execution, service, p, w = dependencies(project_id, workflow_id)
    except BoundaryError:
        return problem('Project / Workflow UUIDまたはownershipが一致しません。', 404)
    except Exception:
        return problem('STOP: 保存先を確認できません。', 503)
    with execution.lock:
        run = execution.runs.get(w)
        try:
            plan, _ = active_plan(service, p, w, run)
            runtime.forms.consume(request.form.get('token'), 'execution:' + action, p, w, revision=run.stamp)
            if request.form.get('human_confirmed') != 'yes':
                raise ValueError('表示内容に対する人の明示確認が必要です。')
            work, paths = service.binding(p, w)
            if action == 'decide':
                if plan.approval_result is not None:
                    raise BoundaryError('既に判断済みです。')
                choice = required(request.form, 'human_decision')
                if choice not in ('approved', 'revision_requested', 'cancelled'):
                    raise ValueError('対応する判断を明示してください。')
                identity, date = (new_decision_identity() if configured() is not None else
                                  (required(request.form, 'approval_id'), required(request.form, 'approved_at')))
                if approval_fact(identity) is not None:
                    raise ValueError('このApproval IDは既に保存されています。上書きしません。')
                comment = request.form.get('comment', '')
                if choice == 'revision_requested' and not comment.strip():
                    raise ValueError('修正要求を入力してください。')
                refs, delegated = delegated_inputs(work, paths, identity) if choice == 'approved' else ({}, None)
                command = RequestPlanApprovalInput(paths['plan'], choice, comment, identity, date, paths['state'], paths['history'])
            else:
                if plan.approval_result is None or plan.approval_result.decision != 'revision_requested':
                    raise BoundaryError('明示的な修正要求がありません。')
                preparation = configured()
                if preparation is not None:
                    slot = preparation.binding(work, paths)
                    template = paths.get('revision_template')
                    if template is None:
                        raise ValueError('正式修正テンプレートが関連付けられていません。')
                    revised = slot / ('plan-revision-' + str(uuid4()) + '.md')
                else:
                    template = explicit_path(required(request.form, 'revision_template'))
                    revised = explicit_path(required(request.form, 'revised_plan'))
                if not template.is_file() or revised.exists():
                    raise ValueError('正式修正テンプレートと未使用のPlan保存先が必要です。')
                refs = {'revision_template': template}
                command = ReviseImplementationPlanInput(paths['plan'], plan.approval_result.revision_request,
                    paths['specification'], request.form.get('related_information') or None,
                    template, paths['state'], paths['history'])
        except BoundaryError as exc:
            return problem(str(exc), 409)
        except (ValueError, OSError) as exc:
            return problem('STOP: ' + str(exc), 400)
        except Exception:
            return problem('STOP: 正式入力を確認できません。判断・委任処理は行っていません。', 503)
        try:
            # All approved-path inputs exist before any Human Approval is saved.
            if refs:
                service.record_references(p, w, refs)
            run.result = (run.adapter.decide_plan(command, delegated) if action == 'decide'
                          else run.adapter.revise_plan(command, revised))
        except Exception:
            run.failure = 'STOP: index保存または処理に失敗しました。一部保存済みの可能性があります。自動再送しません。'
        retain(runtime, service, p, w, run)
        return redirect(location(p, w), code=303)
