"""Human decision presentation and explicit Final POST; no new formal authority."""
from dataclasses import asdict, dataclass
import json

from flask import Blueprint, current_app, redirect, render_template, request, url_for

from application.final_approval_decision import FinalApprovalDecision
from application.final_approval_target import FinalApprovalTargetOutput
from application.final_approval_workflow import HumanFinalDecisionInput, FinalApprovalWorkflowOutput
from application.final_approval_workflow_snapshot import load_checkpoint
from human_control.application_adapter import ApplicationPorts, WorkflowObservation
from human_control.execution_ui import digest, snapshot, approval_fact, required, retain
from human_control.projects import ProjectService
from human_control.project_ui import FIELDS, problem
from human_control.web_runtime import BoundaryError
from human_control.workflow_ui import context
from human_control.workflows import WorkflowService
from human_control.workflow_preparation import new_decision_identity, lines

pages = Blueprint('human_decisions', __name__,
    url_prefix='/control/projects/<project_id>/workflows/<workflow_id>/decisions')
CHOICES = {
    FinalApprovalDecision.FINAL_APPROVAL.value: '最終承認',
    FinalApprovalDecision.IMPLEMENTATION_CORRECTION.value: '実装修正への差し戻し',
    FinalApprovalDecision.PLAN_REVISION.value: 'Plan修正への差し戻し',
    FinalApprovalDecision.SPECIFICATION_RECONSIDERATION.value: 'Specification再検討への差し戻し',
    FinalApprovalDecision.CANCELLATION.value: '中止',
}


@dataclass
class Attempt:
    """Process-local POST attempt, not a persisted checkpoint or decision record."""
    project_id: object
    output: FinalApprovalWorkflowOutput | None = None
    failure: str = ''


def decision_context(project_id, workflow_id):
    data = context(project_id, workflow_id)
    runtime, work = data['runtime'], data['work']
    p, w = work.project_id, work.workflow_id
    execution = current_app.extensions['human_execution']
    run = execution.runs.get(w)
    attempt = current_app.extensions['human_decisions'].get(w)
    if attempt is not None and attempt.project_id != p:
        raise BoundaryError('Human decision ownership mismatch')
    projects = ProjectService(runtime.require_repository())
    items = projects.constitution(p)
    projection = data['result'].projection
    observation = data['observation']
    latest = observation.outputs[-1] if observation and observation.outputs else None
    actual = (attempt.output if attempt and attempt.output else
              latest if isinstance(latest, FinalApprovalWorkflowOutput) else None)
    data.update(items=items, gate=projects.workflow_start_gate(p), projection=projection,
        attempt=attempt, actual=actual, token=None, target=None, materials={}, ready=False,
        choices=CHOICES, fields=FIELDS, failure='', checkpoint=None)
    if attempt is not None:
        data['failure'] = attempt.failure
        return data
    if run is not None and (run.failure or run.result is None or not run.result.success):
        data['failure'] = run.failure or '直前の実行が成功していません。実結果を確認してください。'
        return data
    if not projection or not projection.reconstructed or projection.resume_point != 'FINAL_APPROVAL':
        return data
    if run is None and not callable(execution.factory):
        data['failure'] = 'STOP: Final実行用依存が未設定です。正式な依存を設定してください。'
        return data
    checkpoint = projection.checkpoint
    # T5 just validated the formal target, ownership, receipts and current artifacts.
    target = load_checkpoint(checkpoint)
    if type(target) is not FinalApprovalTargetOutput:
        raise BoundaryError('Human waiting Final checkpoint required')
    service = WorkflowService(runtime.require_repository())
    work, paths = service.binding(p, w)
    materials = {
        '最終承認対象': json.dumps(asdict(target.artifact), ensure_ascii=False, indent=2),
        '実装Evidence': target.request.implementation_evidence_reference.read_text(encoding='utf-8'),
        '変更差分': target.request.git_diff_reference.read_text(encoding='utf-8'),
        'Review報告': target.request.review_report_reference.read_text(encoding='utf-8'),
    }
    stamp = digest((data['stamp'], asdict(target), items, snapshot(paths, work.approval_id), materials))
    data.update(ready=True, target=target, checkpoint=checkpoint, materials=materials, decision_stamp=stamp,
                formal_snapshot=snapshot(paths, work.approval_id))
    return data


@pages.get('')
def detail(project_id, workflow_id):
    try:
        data = decision_context(project_id, workflow_id)
        if data['ready']:
            work = data['work']
            data['token'] = data['runtime'].forms.issue('decision:final', work.project_id,
                work.workflow_id, revision=data['decision_stamp'])
        return render_template('human_decision.html', **data)
    except BoundaryError:
        return problem('STOP: Project / Workflow UUIDまたはownershipが一致しません。', 404)
    except Exception:
        return problem('STOP: 判断材料の読み取り・検証に失敗しました。正式記録を確認してください。', 503)


def human_input():
    if request.form.get('human_confirmed') != 'yes':
        raise ValueError('対象と判断内容のHuman明示確認が必要です。')
    choice = FinalApprovalDecision(required(request.form, 'decision'))
    reason = required(request.form, 'reason')
    managed = 'human_preparation' in current_app.extensions
    references = list(lines(request.form, 'references')) if managed else json.loads(required(request.form, 'references'))
    if not isinstance(references, list) or any(not isinstance(v, str) or not v.strip() for v in references):
        raise ValueError('参照情報には文字列のJSON配列を指定してください。参照なしは [] と明示してください。')
    identity = request.form.get('approval_id', '')
    date = request.form.get('approved_at', '')
    if choice is FinalApprovalDecision.FINAL_APPROVAL:
        identity, date = new_decision_identity() if managed else (required(request.form, 'approval_id'), required(request.form, 'approved_at'))
        if approval_fact(identity) is not None:
            raise ValueError('保存済みApproval IDは上書きできません。')
    return HumanFinalDecisionInput(choice.value, reason, identity, date,
                                   request.form.get('comment', ''), tuple(references))


@pages.post('/final')
def final(project_id, workflow_id):
    runtime = current_app.extensions['human_control']
    execution = current_app.extensions['human_execution']
    try:
        p, w = runtime.target(project_id, workflow_id)
    except BoundaryError:
        return problem('STOP: Project / Workflow UUIDまたはownershipが一致しません。', 404)
    except Exception:
        return problem('STOP: 保存先を確認できません。', 503)
    with execution.lock:
        try:
            data = decision_context(p, w)
            if not data['ready']:
                raise BoundaryError('STOP: 対象は判断待ちではないか、既に操作済み・正式情報が不整合です。再実行しません。')
            runtime.forms.consume(request.form.get('token'), 'decision:final', p, w,
                                  revision=data['decision_stamp'])
            human = human_input()
        except BoundaryError as exc:
            return problem(str(exc), 409)
        except ValueError as exc:
            return problem('STOP: ' + str(exc), 400)
        except Exception:
            return problem('STOP: 判断対象の再検証に失敗しました。処理を開始していません。', 409)
        attempt = current_app.extensions['human_decisions'][w] = Attempt(p)
        service = WorkflowService(runtime.require_repository())
        run = execution.runs.get(w)
        try:
            if run is not None:
                before = len(run.adapter.observation().outputs)
                run.result = run.adapter.decide_final(human)
                outputs = run.adapter.observation().outputs
                if len(outputs) > before and isinstance(outputs[-1], FinalApprovalWorkflowOutput):
                    attempt.output = outputs[-1]
                if not run.result.success:
                    attempt.failure = 'STOP: ' + run.result.reason
                retain(runtime, service, p, w, run)
                if run.failure:
                    attempt.failure = run.failure
            else:
                # Restore only the existing Final contract, never a synthetic T4 adapter.
                ports = execution.factory(service, data['work'])
                if not isinstance(ports, ApplicationPorts) or not callable(getattr(ports.final, 'resume', None)):
                    raise ValueError('Final execution dependency unavailable')
                # Construction must not make a stale target executable. Repeat T5's
                # read-only validation independently of the UI attempt marker.
                current = context(p, w)
                projection = current['result'].projection
                work, paths = service.binding(p, w)
                if (not projection or not projection.reconstructed or projection.resume_point != 'FINAL_APPROVAL'
                        or projection.checkpoint != data['checkpoint']
                        or current['stamp'] != data['stamp']
                        or ProjectService(service.repository).constitution(p) != data['items']
                        or digest(snapshot(paths, work.approval_id)) != digest(data['formal_snapshot'])):
                    raise BoundaryError('正式情報が依存構成中に変化しました。')
                output = ports.final.resume(data['checkpoint'], human)
                if not isinstance(output, FinalApprovalWorkflowOutput):
                    raise ValueError('Actual FinalApprovalWorkflowOutput required')
                attempt.output = output
                previous = runtime.outputs.get(p, w)
                runtime.outputs.put(WorkflowObservation(p, w, (*previous.outputs, output) if previous else (output,)))
                service.record_references(p, w, {key: path for key, path in
                    dict(final_result=output.diagnostic_path, merge_checkpoint=output.retry_snapshot_path).items()
                    if path is not None})
                if not output.success:
                    attempt.failure = 'STOP: ' + (output.stop_reason or 'Final処理に失敗しました。')
        except Exception:
            attempt.failure = ('STOP: Final処理・依存取得・結果の保存に失敗しました。正式記録と実結果を保持しています。'
                               '一部保存済みの可能性があります。自動再試行・rollbackはしません。')
        return redirect(url_for('human_workflows.detail', project_id=p, workflow_id=w), code=303)
