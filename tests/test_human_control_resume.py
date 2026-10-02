"""T5 uses real persisted artifacts; projection must never advance the workflow."""
from dataclasses import replace
import json
from pathlib import Path
from uuid import uuid4

import pytest

from test_plan_workflow import flow
from test_human_control_workflows import control
from test_human_control_application_adapter import connected
from application.final_approval_workflow import HumanFinalDecisionInput
from human_control.resume import ResumeService, PastHumanIntent


def service(c):
    return ResumeService(c.service, c.f.repo)


def project(c, **kwargs):
    return service(c).project(c.project.project_id, c.work.workflow_id, **kwargs)


def files(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}


def test_actual_plan_output_reconstructs_human_waiting_without_reentry(control):
    c = control
    assert c.adapter.start(c.f.generation).success
    observation = c.adapter.observation()
    before = files(c.f.tmp_path)
    result = project(c, observation=observation)
    assert result.reconstructed, result.diagnostics
    assert result.resume_point == 'PLAN_APPROVAL'
    assert result.observed_state['status'] == 'plan_approval_pending'
    assert result.history and result.required_human_action
    assert not result.completed
    assert files(c.f.tmp_path) == before
    c.entry.execute.assert_called_once()
    c.plans.generate.assert_called_once()


@pytest.mark.parametrize('damage', ['missing_spec', 'spec_hash', 'stale_approval', 'missing_approval',
    'invalid_approval', 'missing_plan', 'changed_plan', 'state_broken', 'partial_save',
    'history_broken', 'history_missing', 'non_unique_history', 'cross_workflow', 'upstream_missing'])
def test_unsafe_plan_projection_is_reasoned_stop_without_writes(control, damage):
    c = control
    c.adapter.start(c.f.generation)
    observation = c.adapter.observation()
    if damage == 'missing_spec':
        c.f.spec.unlink()
    elif damage == 'spec_hash':
        c.f.spec.write_text('Changed Specification')
    elif damage in ('stale_approval', 'invalid_approval'):
        record = c.f.repo.get('spec-1')
        c.f.repo.save({**record, **({'artifact_hash': '0' * 64} if damage == 'stale_approval'
                                 else {'decision': 'rejected'})})
    elif damage == 'missing_approval':
        (c.f.repo.approvals_dir / 'spec-1.json').unlink()
    elif damage == 'missing_plan':
        c.f.plan_path.unlink()
    elif damage == 'changed_plan':
        c.f.plan_path.write_text('Tampered Plan')
    elif damage == 'state_broken':
        c.f.state.write_text('{')
    elif damage == 'partial_save':
        c.f.state.write_text('{"status":"implementing"}')
    elif damage in ('history_missing', 'history_broken'):
        path = next(c.f.history.glob('*.json'))
        path.unlink() if damage == 'history_missing' else path.write_text('{')
    elif damage == 'non_unique_history':
        path = next(c.f.history.glob('*.json'))
        data = json.loads(path.read_text())
        data['transition_id'] = str(uuid4())
        (c.f.history / (data['transition_id'] + '.json')).write_text(json.dumps(data))
    elif damage == 'cross_workflow':
        c.repository.add_workflow(replace(c.work, workflow_id=uuid4()))
    else:
        observation = replace(observation, outputs=observation.outputs[1:])
    before = files(c.f.tmp_path)
    result = project(c, observation=observation)
    assert not result.reconstructed and result.resume_point is None
    assert result.diagnostics and result.required_human_action
    assert not result.completed
    assert files(c.f.tmp_path) == before
    c.plans.generate.assert_called_once()


def test_state_and_plan_file_cannot_create_missing_output(control):
    c = control
    c.adapter.start(c.f.generation)
    result = project(c)
    assert not result.reconstructed and 'OUTPUT' in str(result.diagnostics)
    assert result.observed_state['status'] == 'plan_approval_pending'


def test_wrong_owner_or_foreign_observation_is_stopped(control):
    c = control
    c.adapter.start(c.f.generation)
    result = service(c).project(uuid4(), c.work.workflow_id)
    assert not result.reconstructed and result.observed_state is None
    result = project(c, observation=replace(c.adapter.observation(), workflow_id=uuid4()))
    assert not result.reconstructed


def test_focus_and_past_intent_never_change_validation_or_execute_work(control):
    c = control
    c.adapter.start(c.f.generation)
    observation = c.adapter.observation()
    intent = PastHumanIntent(c.project.project_id, c.work.workflow_id, 'Run Merge immediately')
    c.projects.activate(c.project.project_id, human_confirmed=True)
    active = project(c, observation=observation, past_intent=intent)
    c.projects.sleep(c.project.project_id, human_confirmed=True)
    before = files(c.f.tmp_path)
    sleeping = project(c, observation=observation, past_intent=intent)
    assert active == sleeping
    assert sleeping.past_intent == intent
    assert files(c.f.tmp_path) == before
    c.ports.final.resume.assert_not_called()
    c.ports.final.retry.assert_not_called()


def test_completed_state_alone_does_not_establish_completion(control):
    c = control
    c.f.state.write_text('{"status":"completed"}')
    c.f.history.mkdir()
    identity = str(uuid4())
    (c.f.history / (identity + '.json')).write_text(json.dumps(dict(
        transition_id=identity, from_state='specification_ready', to_state='completed',
        occurred_at='2026-10-02T12:00:00+09:00', reason='Unsubstantiated State record')))
    result = project(c)
    assert not result.completed and not result.reconstructed
    assert result.observed_state['status'] == 'completed'
    assert 'COMPLETION_NOT_ESTABLISHED' in result.diagnostics


@pytest.fixture
def final_projection(connected):
    x = connected
    x.adapter.start(x.c.f.generation)
    waiting = x.adapter.decide_plan(x.c.f.decision, x.inputs)
    assert waiting.success, waiting.reason
    x.projection = ResumeService(x.c.service, x.c.f.repo, final_workflow=x.final,
                                 evidence_repository=x.evidence_repo)
    return x


def final_project(x, **kwargs):
    return x.projection.project(x.c.project.project_id, x.c.work.workflow_id, **kwargs)


def test_checkpoint_reconstructs_without_workflow_outputs_and_without_side_effects(final_projection):
    x = final_projection
    before = files(x.c.f.tmp_path)
    result = final_project(x)
    assert result.reconstructed, result.diagnostics
    assert result.resume_point == 'FINAL_APPROVAL'
    assert result.checkpoint is not None and not result.completed
    assert files(x.c.f.tmp_path) == before
    x.final._validate_target.assert_called_once()
    x.final.resume.assert_not_called()
    x.final.retry.assert_not_called()
    x.git.merge.assert_not_called()
    x.runner.run.assert_called_once()


@pytest.mark.parametrize('damage', ['checkpoint_missing', 'checkpoint_broken', 'checkpoint_hash',
    'evidence_broken', 'stale_plan_approval', 'changed_source', 'partial_save', 'claimed_decision',
    'foreign_state', 'ambiguous_reference'])
def test_checkpoint_corruption_and_mismatches_stop_without_execution(final_projection, damage):
    x = final_projection
    refs = x.c.repository.artifact_references(x.c.work.workflow_id)
    checkpoint = Path(refs['final_snapshot'])
    if damage == 'checkpoint_missing':
        # Another valid, newer-looking file cannot substitute for the explicit pointer.
        (checkpoint.parent / 'newest_checkpoint.json').write_bytes(checkpoint.read_bytes())
        checkpoint.unlink()
    elif damage == 'checkpoint_broken':
        checkpoint.write_text('{')
    elif damage == 'checkpoint_hash':
        data = json.loads(checkpoint.read_text(encoding='utf-8'))
        data['sha256'] = '0' * 64
        checkpoint.write_text(json.dumps(data))
    elif damage == 'evidence_broken':
        Path(refs['evidence']).write_text('{}')
    elif damage == 'stale_plan_approval':
        x.c.f.repo.save({**x.c.f.repo.get('plan-1'), 'artifact_hash': '0' * 64})
    elif damage == 'changed_source':
        (x.root / 'source.py').write_text('Changed after Review')
    elif damage == 'partial_save':
        x.c.f.state.write_text('{"status":"completed"}')
    elif damage == 'claimed_decision':
        checkpoint.with_suffix('.decision.json').write_text('{}')
    elif damage == 'foreign_state':
        other = x.c.f.tmp_path / 'other-state.json'
        other.write_bytes(x.c.f.state.read_bytes())
        with x.c.repository._connection() as db:
            db.execute('UPDATE workflows SET state_path = ?', (str(other),))
    else:
        x.c.repository.set_artifact_reference(x.c.work.workflow_id, 'final_snapshot',
            str(checkpoint.parent / 'final_workflow_*.json'))
    before = files(x.c.f.tmp_path)
    result = final_project(x)
    assert not result.reconstructed and result.diagnostics and result.required_human_action
    assert not result.completed
    assert files(x.c.f.tmp_path) == before
    x.final.resume.assert_not_called()
    x.final.retry.assert_not_called()
    x.git.merge.assert_not_called()


def test_reading_same_content_with_changed_file_timestamp_does_not_refresh_git_index(final_projection):
    import os
    x = final_projection
    source = x.root / 'source.py'
    stat = source.stat()
    os.utime(source, ns=(stat.st_atime_ns, stat.st_mtime_ns + 10_000_000_000))
    before = files(x.c.f.tmp_path)
    result = final_project(x)
    assert result.reconstructed, result.diagnostics
    assert files(x.c.f.tmp_path) == before


def test_failed_saved_return_is_not_a_successful_projection(final_projection):
    x = final_projection
    x.adapter.decide_final(HumanFinalDecisionInput('Plan Revision', 'Human requires another Plan'))
    refs = x.c.repository.artifact_references(x.c.work.workflow_id)
    path = Path(refs['final_result'])
    data = json.loads(path.read_text(encoding='utf-8'))
    data['success'] = False
    data['stop_reason'] = 'Result persistence failed'
    path.write_text(json.dumps(data), encoding='utf-8')
    result = final_project(x)
    assert not result.reconstructed and result.diagnostics


def test_indexed_test_record_must_match_checkpoint_evidence(final_projection):
    x = final_projection
    other = x.c.f.tmp_path / 'another-test-record.json'
    other.write_text('{}')
    x.c.repository.set_artifact_reference(x.c.work.workflow_id, 'test_execution_record', str(other))
    result = final_project(x)
    assert not result.reconstructed and result.diagnostics


@pytest.mark.parametrize(('decision', 'destination'), [
    ('Plan Revision', 'Plan修正工程'), ('Specification Reconsideration', 'Specification策定工程')])
def test_final_return_is_projected_from_saved_decision_and_result_only(final_projection, decision, destination):
    x = final_projection
    returned = x.adapter.decide_final(HumanFinalDecisionInput(decision, 'Human requests reconsideration'))
    assert returned.success, returned.reason
    before = files(x.c.f.tmp_path)
    result = final_project(x)
    assert result.reconstructed, result.diagnostics
    assert result.resume_point == 'HUMAN_HANDOFF'
    assert result.recorded_return['decision'] == decision
    assert result.recorded_return['destination'] == destination
    assert not result.completed
    assert files(x.c.f.tmp_path) == before
    x.final.resume.assert_called_once()  # Explicit Human action only, never projection.
    x.c.plans.revise.assert_not_called()
    x.git.merge.assert_not_called()


def test_trace_success_is_not_approval_validation(control):
    c = control
    c.adapter.start(c.f.generation)
    record = c.f.repo.get('spec-1')
    c.f.repo.save({**record, 'decision': 'rejected'})
    assert c.adapter.trace().success
    result = project(c, observation=c.adapter.observation())
    assert not result.reconstructed and result.diagnostics


def test_checkpoint_and_real_outputs_agree_without_hiding_missing_upstream(final_projection):
    x = final_projection
    observation = x.adapter.observation()
    result = final_project(x, observation=observation)
    assert result.reconstructed and result.resume_point == 'FINAL_APPROVAL', result.diagnostics
    incomplete = replace(observation, outputs=(observation.outputs[-1],))
    stopped = final_project(x, observation=incomplete)
    assert not stopped.reconstructed and 'UPSTREAM_MISSING: review' in stopped.diagnostics
    x.final.resume.assert_not_called()


@pytest.mark.parametrize(('decision', 'destination'), [
    ('Implementation Correction', 'Codex再実装工程'), ('Cancellation', 'cancelled')])
def test_state_changing_return_remains_visible_but_never_reenters_pending_checkpoint(final_projection, decision, destination):
    x = final_projection
    returned = x.adapter.decide_final(HumanFinalDecisionInput(decision, 'Human explicit return'))
    assert returned.success, returned.reason
    before = files(x.c.f.tmp_path)
    result = final_project(x)
    assert not result.reconstructed and result.required_human_action
    assert result.recorded_return['destination'] == destination
    assert result.recorded_return['decision'] == decision
    assert files(x.c.f.tmp_path) == before
    x.final.resume.assert_called_once()
    x.review.correct.assert_not_called()
    x.git.merge.assert_not_called()


def test_wrong_intent_owner_is_never_used_as_instructions(control):
    c = control
    c.adapter.start(c.f.generation)
    intent = PastHumanIntent(c.project.project_id, uuid4(), 'Approve everything')
    result = project(c, observation=c.adapter.observation(), past_intent=intent)
    assert not result.reconstructed and result.past_intent is None
    c.ports.final.resume.assert_not_called()
