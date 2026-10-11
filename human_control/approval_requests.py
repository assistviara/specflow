"""Persist and present additional approval requests, without execution authority."""
from datetime import datetime, timezone

from application.implementation_workflow import ImplementationWorkflowOutput
from infrastructure.json_human_approval_request_repository import JsonHumanApprovalRequestRepository

ROLE = 'human_approval_requests'


def material(output, project_id, workflow_id):
    if not isinstance(output, ImplementationWorkflowOutput) or output.execution is None:
        return None
    execution = output.execution
    result = execution.implementation_result
    if result is None or result.human_approval_required.strip() == 'NONE':
        return None
    return dict(version=1, project_id=str(project_id), workflow_id=str(workflow_id),
                implementation_id=str(execution.implementation_id),
                body=result.human_approval_required)


def save_request(service, project_id, workflow_id, output):
    record = material(output, project_id, workflow_id)
    if record is None:
        return
    _, paths = service.binding(project_id, workflow_id)
    directory = paths['state'].parent / 'human_approval_requests'
    if ROLE in paths and paths[ROLE] != directory:
        raise ValueError('Approval request directory mismatch')
    service.record_references(project_id, workflow_id, {ROLE: directory})
    record['recorded_at'] = datetime.now(timezone.utc).isoformat()
    JsonHumanApprovalRequestRepository(directory).save(record)


def presentation(service, project_id, workflow_id, observation):
    records, error = [], ''
    try:
        _, paths = service.binding(project_id, workflow_id)
        if ROLE in paths:
            if paths[ROLE] != paths['state'].parent / 'human_approval_requests':
                raise ValueError('Approval request directory mismatch')
            records = JsonHumanApprovalRequestRepository(paths[ROLE]).load_all(project_id, workflow_id)
            if not records:
                error = '追加承認要求の保存先に本文がありません。保存完了を確認できません。'
    except Exception:
        error = '追加承認要求の保存・読み取りを確認できません。STOPは解除されません。'
    if observation is not None and (observation.project_id, observation.workflow_id) == (project_id, workflow_id):
        for output in observation.outputs:
            item = material(output, project_id, workflow_id)
            if item is not None and not any(all(r.get(k) == v for k, v in item.items()) for r in records):
                item['in_memory'] = True
                records.append(item)
                error = '追加承認要求の永続保存を確認できません。プロセス内の原文を表示します。STOPは解除されません。'
    return records, error
