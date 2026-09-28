from dataclasses import replace
import json

import pytest

from test_plan_workflow import flow
from test_implementation_workflow import implementation
from test_evidence_workflow import evidence_flow
from test_review_workflow import review_flow, correction_flow
from test_final_approval_workflow import review_ready, final_case, configure_merge, approve


def trace_input(final_case, result):
    from application.workflow_trace import WorkflowTraceInput
    c, _, _, review, _ = final_case
    evidence = review.request.upstream
    implementation = evidence.request.upstream
    plan = implementation.request.upstream
    return WorkflowTraceInput(c.case.flow.state, c.case.flow.history,
        (plan.entry, plan, implementation, evidence, review, result))


def test_workflow_trace_connects_completed_target1_to_target6_history_and_artifacts(final_case):
    from application.workflow_trace import WorkflowTraceUseCase
    configure_merge(final_case)
    result = final_case[2].resume(final_case[4].snapshot_path, approve())
    request = trace_input(final_case, result)
    before = {p: p.read_bytes() for p in request.state_file.parent.rglob('*') if p.is_file()}
    trace = WorkflowTraceUseCase().execute(request)
    assert trace.success, trace.diagnostics
    assert trace.workflow_success and trace.completed
    assert trace.current_state == result.current_state
    assert trace.history[-1].record['to_state'] == 'completed'
    assert len(trace.stages) == 6
    values = [item.value for item in trace.references]
    assert 'spec-1' in values and 'plan-1' in values and 'final-1' in values
    assert result.merge.operation_id in values
    assert 'b' * 40 in values
    assert before == {p: p.read_bytes() for p in request.state_file.parent.rglob('*') if p.is_file()}


@pytest.fixture
def completed_case(final_case):
    configure_merge(final_case)
    result = final_case[2].resume(final_case[4].snapshot_path, approve())
    assert result.completed
    return trace_input(final_case, result)


def observe(request):
    from application.workflow_trace import WorkflowTraceUseCase
    return WorkflowTraceUseCase().execute(request)


@pytest.mark.parametrize('damage', ['missing_first', 'missing_middle', 'missing_last',
    'broken_json', 'wrong_id', 'wrong_state', 'state_unreadable', 'state_missing', 'wrong_history_root'])
def test_damaged_persistence_cannot_be_a_successful_trace(completed_case, damage):
    request = completed_case
    paths = sorted(request.history_dir.glob('*.json'),
        key=lambda p: json.loads(p.read_text())['occurred_at'])
    if damage.startswith('missing_'):
        paths[{'missing_first': 0, 'missing_middle': len(paths) // 2, 'missing_last': -1}[damage]].unlink()
    elif damage == 'broken_json':
        paths[-1].write_text('{')
    elif damage == 'wrong_id':
        data = json.loads(paths[-1].read_text())
        data['transition_id'] = 'other'
        paths[-1].write_text(json.dumps(data))
    elif damage == 'wrong_state':
        request.state_file.write_text('{"status":"reviewing"}')
    elif damage == 'state_unreadable':
        request.state_file.write_text('{')
    elif damage == 'state_missing':
        request.state_file.unlink()
    else:
        request = replace(request, history_dir=request.history_dir / 'absent')
    trace = observe(request)
    assert not trace.success and trace.diagnostics
    assert trace.completed  # Original Target 6 result is never rewritten.
    if damage in ('state_unreadable', 'state_missing'):
        assert trace.current_state is None and trace.state_status == 'unknown'


@pytest.mark.parametrize('index', range(6))
def test_missing_stage_is_not_a_complete_trace(completed_case, index):
    request = replace(completed_case, outputs=completed_case.outputs[:index] + completed_case.outputs[index+1:])
    assert not observe(request).success


@pytest.mark.parametrize('index', range(6))
def test_failed_gate_is_not_reinterpreted_as_success(completed_case, index):
    outputs = list(completed_case.outputs)
    outputs[index] = replace(outputs[index], **({'can_generate_plan': False} if index == 0 else {'success': False}))
    trace = observe(replace(completed_case, outputs=tuple(outputs)))
    assert not trace.success
    assert not trace.stages[index].workflow_success


def test_partial_completed_state_does_not_override_failed_completion(final_case, monkeypatch):
    import application.state_transition as persistence
    configure_merge(final_case)
    original = persistence.save_state_transition_history
    def fail_completion(directory, transition):
        if transition['to_state'] == 'completed':
            raise OSError('History storage full')
        return original(directory, transition)
    monkeypatch.setattr(persistence, 'save_state_transition_history', fail_completion)
    result = final_case[2].resume(final_case[4].snapshot_path, approve())
    trace = observe(trace_input(final_case, result))
    assert trace.current_state['status'] == 'completed' and trace.state_status == 'saved'
    assert not trace.workflow_success and not trace.success and not trace.completed
    assert any(t.history_status == 'not_saved' for t in trace.transitions)
    assert trace.stops[-1].reason == result.stop_reason
    assert trace.stops[-1].required_human_action == result.completion.required_human_action


def test_plan_waiting_uses_stage_and_result_and_retains_unknowns(flow):
    from application.workflow_trace import WorkflowTraceInput
    draft = flow.use_case.generate(flow.entry, flow.generation, flow.plan_path)
    trace = observe(WorkflowTraceInput(flow.state, flow.history, (flow.entry, draft)))
    assert trace.success and trace.waiting == ('PLAN_APPROVAL',)
    assert trace.stops[-1].affected_scope is None
    assert trace.stops[-1].restart_point is None
    assert trace.stops[-1].required_human_action is None
    assert trace.stops[-1].artifact_references
    assert not observe(WorkflowTraceInput(flow.state, flow.history, (flow.entry,))).waiting


def test_final_waiting_is_not_merge_authorization(final_case):
    trace = observe(trace_input(final_case, final_case[4]))
    assert trace.success and trace.waiting == ('FINAL_APPROVAL',)
    assert not trace.completed


def test_retry_authorization_and_correction_are_separate(final_case):
    from application.technical_merge_retry import MergeRetryAuthorization
    configure_merge(final_case)
    _, git, workflow, _, waiting = final_case
    successful = git.merge.return_value
    git.merge.return_value = replace(successful, returncode=1, errors=('Temporary failure',))
    failed = workflow.resume(waiting.snapshot_path, approve())
    trace = observe(trace_input(final_case, failed))
    assert not trace.success and trace.waiting == ('MERGE_RETRY_AUTHORIZATION',)
    assert trace.stops[-1].required_human_action == failed.merge.required_human_action
    git.retry_merge.return_value = successful
    retried = workflow.retry(failed.retry_snapshot_path,
        MergeRetryAuthorization(failed.merge.operation_id, True, 'Human authorized safe retry'))
    request = trace_input(final_case, retried)
    request = replace(request, outputs=(*request.outputs[:-1], failed, retried))
    after = observe(request)
    assert after.success, after.diagnostics
    assert not after.waiting and after.completed
    assert after.stages[-2].snapshot['merge']['operation_id'] == after.stages[-1].snapshot['merge']['operation_id']
    assert after.stages[-1].snapshot['merge']['retry_count'] == 1
    assert after.stages[4].snapshot['correction_count'] == 0
    assert after.stages[-1].snapshot['approval']['approval_record']['approval_id'] == 'final-1'


def test_stop_reason_is_not_reclassified_and_snapshots_are_detached(flow):
    from application.workflow_trace import WorkflowTraceInput
    failed = replace(flow.entry, can_generate_plan=False)
    trace = observe(WorkflowTraceInput(flow.state, flow.history, (failed,)))
    assert not trace.success
    assert trace.stops[-1].reason is None
    trace.stages[0].snapshot['current_state']['status'] = 'tampered'
    assert failed.current_state['status'] == 'plan_generating'


@pytest.mark.parametrize('kind', ['empty', 'unsupported'])
def test_missing_or_unknown_output_is_not_success(flow, kind):
    from application.workflow_trace import WorkflowTraceInput
    trace = observe(WorkflowTraceInput(flow.state, flow.history, () if kind == 'empty' else (object(),)))
    assert not trace.success and trace.diagnostics


def review_request(c, review):
    from application.workflow_trace import WorkflowTraceInput
    evidence = review.request.upstream
    implementation = evidence.request.upstream
    plan = implementation.request.upstream
    return WorkflowTraceInput(c.case.flow.state, c.case.flow.history,
        (plan.entry, plan, implementation, evidence, review))


def test_review_human_handoff_preserves_reason_action_and_references(review_flow):
    from test_review_workflow import evaluation, AIResponse
    c = review_flow
    original = c.runner.run.side_effect
    def run(request):
        if request.prompt.startswith('# Review Result Evaluation'):
            data = evaluation('HUMAN_REVIEW_REQUIRED')
            data['references'] = ['review.prepared.review_input.implementation_plan.content']
            data['human_questions'] = ['Human must clarify the required behavior']
            return AIResponse(json.dumps(data), True)
        return original(request)
    c.runner.run.side_effect = run
    result = c.use_case.start(c.request)
    trace = observe(review_request(c, result))
    assert trace.success, trace.diagnostics
    assert trace.waiting == ('REVIEW_HUMAN_HANDOFF',)
    assert trace.stops[-1].reason == result.handoff.reason
    assert trace.stops[-1].required_human_action == result.handoff.required_human_action
    assert any(r.value == result.handoff.artifact_references for r in trace.stops[-1].artifact_references)


def test_critical_change_waiting_uses_structured_execution_result(implementation):
    from application.workflow_trace import WorkflowTraceInput
    from test_implementation_workflow import mutate_trace
    flow, request, runner, use_case, _ = implementation
    def alter(events):
        for event in events:
            item = event.get('item', {})
            if 'text' in item:
                item['text'] = item['text'].replace('## Human Approval Required\nNONE',
                    '## Human Approval Required\nScope expansion needs Human')
    mutate_trace(runner, alter)
    result = use_case.execute(request)
    trace = observe(WorkflowTraceInput(flow.state, flow.history,
        (request.upstream.entry, request.upstream, result)))
    assert not trace.success and trace.waiting == ('CRITICAL_CHANGE',)
    assert trace.current_state['status'] == 'critical_approval_pending'
    assert trace.stops[-1].reason == result.stop_reason


def test_correction_preserves_old_evidence_and_new_generation(correction_flow):
    from application.review_workflow import CorrectionStepInput
    c = correction_flow
    result = c.c.use_case.correct(c.first,
        CorrectionStepInput(c.first.review.classification, c.assessments, c.problems, c.retest))
    request = review_request(c.c, result)
    request = replace(request, outputs=(*request.outputs[:-1], c.first, result))
    trace = observe(request)
    assert trace.success, trace.diagnostics
    old = c.first.review.review.prepared.review_input.evidence.identity
    new = result.cycles[-1].evidence.implementation_evidence.identity
    values = [r.value for r in trace.references]
    assert old.evidence_id in values and new.evidence_id in values
    assert any(r.source.endswith('previous_evidence_id') and r.value == old.evidence_id for r in trace.references)
    assert trace.stages[-2].snapshot['correction_count'] == 0
    assert trace.stages[-1].snapshot['correction_count'] == 1


def test_history_read_error_remains_unknown(flow, monkeypatch):
    from pathlib import Path
    from application.workflow_trace import WorkflowTraceInput
    original = Path.read_text
    def fail(path, *args, **kwargs):
        if path.parent == flow.history:
            raise PermissionError('History access denied')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'read_text', fail)
    trace = observe(WorkflowTraceInput(flow.state, flow.history, (flow.entry,)))
    assert not trace.success and trace.state_status == 'saved'
    assert trace.transitions[0].history_status == 'unknown'
    assert trace.history[0].error


@pytest.mark.parametrize('artifact', ['evidence', 'review', 'final'])
def test_missing_saved_artifact_is_not_a_successful_trace(completed_case, artifact):
    outputs = completed_case.outputs
    path = {'evidence': outputs[3].collection.evidence_path,
            'review': outputs[4].artifact_paths[-1],
            'final': outputs[5].snapshot_path}[artifact]
    path.unlink()
    assert not observe(completed_case).success


def test_mismatched_artifact_identity_is_not_a_connected_trace(completed_case):
    from uuid import uuid4
    outputs = list(completed_case.outputs)
    outputs[2] = replace(outputs[2], request=replace(outputs[2].request, implementation_id=uuid4()))
    assert not observe(replace(completed_case, outputs=tuple(outputs))).success


def test_recorded_history_disagreement_retains_both_facts(flow):
    from application.workflow_trace import WorkflowTraceInput
    path = next(flow.history.glob('*.json'))
    record = json.loads(path.read_text())
    record['reason'] = 'Changed persisted reason'
    path.write_text(json.dumps(record))
    trace = observe(WorkflowTraceInput(flow.state, flow.history, (flow.entry,)))
    assert not trace.success
    assert trace.history[0].record['reason'] == 'Changed persisted reason'
    assert trace.transitions[0].transition['reason'] == flow.entry.transition['reason']
    assert trace.transitions[0].history_status == 'inconsistent'


def test_explicit_human_return_retains_existing_restart_destination(final_case):
    from application.final_approval_workflow import HumanFinalDecisionInput
    result = final_case[2].resume(final_case[4].snapshot_path,
        HumanFinalDecisionInput('Plan Revision', 'Human requests scope revision'))
    trace = observe(trace_input(final_case, result))
    assert trace.success and not trace.completed
    assert trace.stops[-1].restart_point == result.routing.destination
    assert trace.stops[-1].reason == 'Human requests scope revision'


def test_critical_handoff_retains_explicit_impact_reference(review_ready):
    from application.review_handoff import CriticalChangeReferences
    c, _, _, review = review_ready
    critical = CriticalChangeReferences('content', 'reason', 'targets', 'known.impact')
    handoff = replace(review.handoff, handoff_type='CRITICAL_CHANGE_APPROVAL',
        request=replace(review.handoff.request, critical_change=critical),
        reason=('CRITICAL_CHANGE',), required_human_action=('Decide supplied change',))
    # Projection unit boundary: an already structured existing handoff.
    result = replace(review, handoff=handoff)
    trace = observe(review_request(c, result))
    assert trace.waiting == ('CRITICAL_CHANGE',)
    assert trace.stops[-1].affected_scope.value == 'known.impact'
    assert trace.stops[-1].affected_scope.source.endswith('critical_change.impact_reference')


def test_unreadable_retry_authorization_is_not_treated_as_absent(final_case):
    configure_merge(final_case)
    _, git, workflow, _, waiting = final_case
    git.merge.return_value = replace(git.merge.return_value, returncode=1, errors=('Temporary failure',))
    failed = workflow.resume(waiting.snapshot_path, approve())
    journal = failed.retry_snapshot_path.parent / 'retry_history' / failed.merge.operation_id
    (journal / 'authorization.json').write_text('{')
    trace = observe(trace_input(final_case, failed))
    assert not trace.success and not trace.waiting
    assert any(d.startswith('RETRY_HISTORY_UNAVAILABLE') for d in trace.diagnostics)


@pytest.mark.parametrize('artifact', ['evidence', 'review', 'final'])
def test_saved_snapshot_must_correspond_to_supplied_output(completed_case, artifact):
    outputs = completed_case.outputs
    path = {'evidence': outputs[3].collection.evidence_path,
            'review': outputs[4].artifact_paths[-1],
            'final': outputs[5].snapshot_path}[artifact]
    path.write_text('{}')
    assert not observe(completed_case).success


def test_equal_timestamps_use_unique_state_links_not_uuid_order(flow):
    from application.workflow_trace import WorkflowTraceInput
    records = [dict(transition_id='z-next', from_state='plan_generating', to_state='plan_approval_pending'),
               dict(transition_id='a-last', from_state='plan_approval_pending', to_state='implementation_ready')]
    for record in records:
        record.update(occurred_at=flow.entry.transition['occurred_at'], reason='Recorded transition')
        (flow.history / (record['transition_id'] + '.json')).write_text(json.dumps(record))
    flow.state.write_text('{"status":"implementation_ready"}')
    output = replace(flow.entry, current_state={'status': 'implementation_ready'})
    trace = observe(WorkflowTraceInput(flow.state, flow.history, (output,)))
    assert trace.success, trace.diagnostics
    assert [h.record['transition_id'] for h in trace.history][-2:] == ['z-next', 'a-last']


def test_cancellation_is_a_terminal_result_not_a_restart_point(final_case):
    from application.final_approval_workflow import HumanFinalDecisionInput
    result = final_case[2].resume(final_case[4].snapshot_path,
        HumanFinalDecisionInput('Cancellation', 'Human cancelled this workflow'))
    trace = observe(trace_input(final_case, result))
    assert trace.success and not trace.completed
    assert trace.current_state['status'] == 'cancelled'
    assert trace.stops[-1].reason == 'Human cancelled this workflow'
    assert trace.stops[-1].restart_point is None
