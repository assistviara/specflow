"""Phase 7 Target 8: existing workflows, explicit Human inputs, offline AI ports.

All Git changes below belong to pytest's disposable repositories. These tests
validate Application Layer behavior, not live model quality or deployment.
"""
from dataclasses import replace
import json
from unittest.mock import Mock

import pytest

from application.final_approval_workflow import FinalApprovalWorkflowUseCase
from application.review_workflow import CorrectionStepInput
from application.workflow_trace import WorkflowTraceInput, WorkflowTraceUseCase
from infrastructure.git_cli_merge_service import GitCliMergeService
from infrastructure.json_merge_retry_repository import JsonMergeRetryRepository
from test_plan_workflow import flow
from test_implementation_workflow import implementation
from test_evidence_workflow import evidence_flow
from test_review_workflow import review_flow, correction_flow
from test_final_approval_workflow import review_ready, final_case, approve, configure_merge
from test_git_repository_state_provider import run_git
from core.ai.ai_response import AIResponse
from test_workflow_entry import workflow
from test_workflow_trace import assert_stop_contract


def review_outputs(review):
    evidence = review.request.upstream
    implementation = evidence.request.upstream
    plan = implementation.request.upstream
    return plan.entry, plan, implementation, evidence, review


def trace(flow, outputs):
    result = WorkflowTraceUseCase().execute(WorkflowTraceInput(flow.state, flow.history, tuple(outputs)))
    assert_stop_contract(result)
    return result


def test_mvp_e2e_correction_to_verified_completion_preserves_approval_and_evidence_lineage(correction_flow):
    c = correction_flow
    f = c.c.case.flow
    root = c.c.case.request.repository
    initial_outputs = review_outputs(c.first)
    entry, plan, implementation, evidence, first = initial_outputs
    assert entry.can_generate_plan and entry.approval_record['decision'] == 'approved'
    assert plan.approval_result.approval_valid and plan.prompt_result.success
    assert implementation.execution.success
    assert implementation.test_state.initial_test_result == 'FAIL'
    assert implementation.test_state.target_test_result == 'PASS'
    assert implementation.test_state.full_test_result == 'PASS'
    assert first.review.classification.result == 'REVISION_REQUIRED'
    assert not first.ready_for_final_approval
    old = evidence.collection.implementation_evidence
    old_bytes = evidence.collection.evidence_path.read_bytes()
    approvals_before = {p: p.read_bytes() for p in f.repo.approvals_dir.glob('*.json')}

    corrected = c.c.use_case.correct(first, CorrectionStepInput(first.review.classification,
        c.assessments, c.problems, c.retest))
    assert corrected.success, corrected.stop_reason
    assert c.calls == ['correction', 'retest']
    assert corrected.correction_count == 1
    cycle = corrected.cycles[-1]
    new = cycle.evidence.implementation_evidence
    assert new.identity.evidence_id != old.identity.evidence_id
    assert new.identity.implementation_id != old.identity.implementation_id
    assert new.identity.previous_evidence_id == old.identity.evidence_id
    assert evidence.collection.evidence_path.read_bytes() == old_bytes
    assert cycle.history.new_evidence_id == new.identity.evidence_id
    assert cycle.history.previous_evidence_id == old.identity.evidence_id
    assert corrected.review == cycle.re_review
    assert corrected.review.review.prepared.review_input.evidence == new
    assert corrected.review.classification.result == 'APPROVED'
    assert corrected.ready_for_final_approval
    assert {p: p.read_bytes() for p in approvals_before} == approvals_before
    assert json.loads(f.state.read_text())['status'] == 'reviewing'

    # Commit the already reviewed bytes in the disposable repository, without
    # changing the reviewed diff. Final Approval binds this exact commit.
    run_git(root, 'add', 'source.py', 'test_source.py')
    run_git(root, 'commit', '-m', 'E2E corrected implementation fixture')
    approved_commit = run_git(root, 'rev-parse', 'HEAD')
    real_git = GitCliMergeService(root)
    git = Mock(wraps=real_git)
    observations = []
    def merge(*args, **kwargs):
        assert json.loads(f.state.read_text())['status'] == 'final_approval_pending'
        observations.append('merge')
        return real_git.merge(*args, **kwargs)
    def verify(*args, **kwargs):
        assert json.loads(f.state.read_text())['status'] == 'final_approval_pending'
        observations.append('verify')
        return real_git.verify_merge(*args, **kwargs)
    git.merge.side_effect, git.verify_merge.side_effect = merge, verify
    final = FinalApprovalWorkflowUseCase(git, f.repo, c.c.case.repository, JsonMergeRetryRepository)
    waiting = final.start(corrected, f.tmp_path / 'mvp_final')
    assert waiting.success and waiting.waiting_for_human, waiting.stop_reason
    assert waiting.target.artifact.head_commit == approved_commit
    assert waiting.target.request.implementation_evidence_reference == cycle.evidence.evidence_path
    no_decision = final.resume(waiting.snapshot_path)
    assert no_decision.waiting_for_human and not no_decision.completed
    git.merge.assert_not_called()
    checks_before = git.get_state.call_count
    completed = final.resume(waiting.snapshot_path, approve())
    assert completed.completed and completed.success, completed.stop_reason
    assert git.get_state.call_count >= checks_before + 2  # readiness and execution recheck
    assert observations == ['merge', 'verify']
    assert completed.ready.merge_ready
    assert completed.merge.result.operation.approved_commit == approved_commit
    assert completed.merge.result.verification.content_matched
    assert completed.merge.result.verification.approved_content_retained
    assert completed.merge.result.verification.verified
    assert run_git(root, 'branch', '--show-current') == 'developer'
    assert (root / 'source.py').read_text() == 'value = 2\n'
    assert run_git(root, 'rev-parse', 'HEAD') == completed.merge.result.operation.post_commit
    assert completed.approval.approval_record['artifact_hash'] == waiting.target.artifact_hash
    observed = trace(f, (*initial_outputs, corrected, waiting, no_decision, completed))
    assert observed.success and observed.completed, observed.diagnostics
    assert observed.current_state['status'] == 'completed'
    assert observed.history[-1].record['to_state'] == 'completed'
    values = [r.value for r in observed.references]
    for identity in ('spec-1', 'plan-1', 'final-1', old.identity.evidence_id,
                     new.identity.evidence_id, completed.merge.operation_id, approved_commit):
        assert identity in values


@pytest.mark.parametrize('failure', ['missing_approval', 'changed_specification'])
def test_mvp_entry_failure_stops_plan_and_preserves_saved_approval(workflow, failure):
    from application.workflow_entry import WorkflowEntryUseCase
    from application.plan_workflow import PlanWorkflowUseCase
    from application.dto import GenerateImplementationPlanInput
    request, approvals, record = workflow
    if failure == 'missing_approval':
        request = replace(request, specification_approval_id='absent')
    else:
        request.specification_path.write_text('Changed after Human approval')
    stopped = WorkflowEntryUseCase(approvals).execute(request)
    assert not stopped.can_generate_plan
    generator = Mock()
    plans = PlanWorkflowUseCase(approvals, generator, Mock(), Mock(), Mock())
    root = request.state_file.parent
    plan_input = GenerateImplementationPlanInput(root, root, request.specification_path, record,
        root, root, {}, root, request.state_file, request.history_dir)
    rejected = plans.generate(stopped, plan_input, root / 'plan.md')
    assert not rejected.success
    generator.execute.assert_not_called()
    observed = WorkflowTraceUseCase().execute(WorkflowTraceInput(
        request.state_file, request.history_dir, (stopped, rejected)))
    assert_stop_contract(observed)
    assert not observed.success and not observed.completed
    assert observed.current_state['status'] == 'specification_ready'
    assert observed.stops and observed.stops[0].reason
    assert approvals.get('spec-001') == record


@pytest.mark.parametrize('decision', ['revision_requested', 'cancelled'])
def test_mvp_plan_human_return_preserves_history_and_requires_new_approval(flow, decision):
    f = flow
    draft = f.use_case.generate(f.entry, f.generation, f.plan_path)
    original = f.plan_path.read_bytes()
    returned = f.use_case.decide(draft, replace(f.decision, human_decision=decision, comment='Fix scope'))
    blocked = f.use_case.generate_prompt(returned, f.prompt)
    assert not blocked.success
    f.prompt_ai.run.assert_not_called()
    outputs = [f.entry, draft, returned, blocked]
    if decision == 'revision_requested':
        f.plan_ai.run.return_value = AIResponse('### REVISED_IMPLEMENTATION_PLAN\n# Revised Plan\n'
            '### CHANGES\nScope fixed\n### PREVIOUS_VERSION_CORRESPONDENCE\nReplaces original', True)
        path = f.tmp_path / 'revised-plan.md'
        revised = f.use_case.revise(returned, f.revision, path)
        assert revised.success and revised.approval_result is None
        assert not f.use_case.generate_prompt(revised, f.prompt).success
        approved = f.use_case.decide(revised, replace(f.decision, implementation_plan_path=path, approval_id='plan-2'))
        prompted = f.use_case.generate_prompt(approved,
            replace(f.prompt, implementation_plan_path=path, implementation_plan_approval_id='plan-2'))
        assert prompted.success
        outputs.extend((revised, approved, prompted))
        assert f.repo.get('plan-1')['decision'] == 'revision_requested'
        assert f.repo.get('plan-2')['decision'] == 'approved'
    else:
        assert returned.approval_result.cancelled
        outputs.append(returned)
    observed = trace(f, outputs)
    assert observed.success and not observed.completed, observed.diagnostics
    assert f.plan_path.read_bytes() == original
    assert observed.current_state['status'] == ('implementation_ready' if decision == 'revision_requested' else 'cancelled')


@pytest.mark.parametrize('failure', ['prompt_error', 'unusable_prompt', 'changed_plan', 'missing_plan_approval'])
def test_mvp_prompt_gate_failure_cannot_start_implementation(flow, failure):
    from test_plan_workflow import approve_draft
    from application.implementation_workflow import ImplementationWorkflowInput, ImplementationWorkflowUseCase, InitialTddApplicability
    from uuid import uuid4
    approved = approve_draft(flow)
    if failure == 'prompt_error':
        flow.prompt_ai.run.return_value = AIResponse('', False, 'transport failure')
    elif failure == 'unusable_prompt':
        flow.prompt_ai.run.return_value = AIResponse('Missing required execution sections', True)
    elif failure == 'changed_plan':
        flow.plan_path.write_text('Changed after approval')
    else:
        (flow.repo.approvals_dir / 'plan-1.json').unlink()
    prompt = flow.use_case.generate_prompt(approved, flow.prompt)
    assert not prompt.success
    preparation, execution = Mock(), Mock()
    service = ImplementationWorkflowUseCase(flow.repo, preparation, execution, Mock())
    inp = ImplementationWorkflowInput(prompt, uuid4(), flow.tmp_path, 'impl/test',
        InitialTddApplicability(flow.plan_path, 'plan-1', 'unused', 'unused', True))
    blocked = service.execute(inp)
    assert not blocked.success
    preparation.prepare.assert_not_called()
    execution.execute.assert_not_called()
    observed = trace(flow, (flow.entry, approved, prompt, blocked))
    assert not observed.success and not observed.completed
    assert observed.stops[-1].reason == blocked.stop_reason


@pytest.mark.parametrize('failure', ['technical_error', 'critical_change'])
def test_mvp_implementation_stop_keeps_state_and_human_boundary(implementation, failure):
    from test_implementation_workflow import mutate_trace
    f, request, runner, service, _ = implementation
    if failure == 'technical_error':
        runner.run.side_effect = RuntimeError('Offline injected technical failure')
    else:
        def alter(events):
            for event in events:
                item = event.get('item', {})
                if 'text' in item:
                    item['text'] = item['text'].replace('## Human Approval Required\nNONE',
                        '## Human Approval Required\nScope expansion requires Human')
        mutate_trace(runner, alter)
    result = service.execute(request)
    observed = trace(f, (request.upstream.entry, request.upstream, result))
    assert not result.success and not observed.success and not observed.completed
    assert observed.stops[-1].reason == result.stop_reason
    assert observed.current_state == result.current_state
    assert observed.waiting == (('CRITICAL_CHANGE',) if failure == 'critical_change' else ())
    runner.run.assert_called_once()


@pytest.mark.parametrize('missing', ['evidence', 'review_input'])
def test_mvp_missing_review_basis_stops_before_review_and_final_approval(review_flow, missing):
    c = review_flow
    if missing == 'evidence':
        c.upstream.collection.evidence_path.unlink()
    else:
        c.request = replace(c.request, upstream=replace(c.upstream,
            handoff=replace(c.upstream.handoff, review_input=None)))
    stopped = c.use_case.start(c.request)
    assert not stopped.success
    c.runner.run.assert_not_called()
    git = Mock()
    final = FinalApprovalWorkflowUseCase(git, c.case.flow.repo, c.case.repository, JsonMergeRetryRepository)
    rejected = final.start(stopped, c.case.flow.tmp_path / 'final')
    assert not rejected.success and not rejected.completed
    git.merge.assert_not_called()
    observed = trace(c.case.flow, (*review_outputs(stopped), rejected))
    assert not observed.success and observed.stops
    assert observed.current_state['status'] == 'implementation_completed'


def test_mvp_human_review_stops_final_approval_without_losing_artifacts(review_flow):
    from test_review_workflow import evaluation
    c = review_flow
    original = c.runner.run.side_effect
    def require_human(request):
        if request.prompt.startswith('# Review Result Evaluation'):
            data = evaluation('HUMAN_REVIEW_REQUIRED')
            data['references'] = ['review.prepared.review_input.implementation_plan.content']
            data['human_questions'] = ['Human must clarify required behavior']
            return AIResponse(json.dumps(data), True)
        return original(request)
    c.runner.run.side_effect = require_human
    result = c.use_case.start(c.request)
    assert result.waiting_for_human and not result.ready_for_final_approval
    observed = trace(c.case.flow, review_outputs(result))
    assert observed.success and not observed.completed
    assert observed.waiting == ('REVIEW_HUMAN_HANDOFF',)
    assert observed.stops[-1].required_human_action == result.handoff.required_human_action
    assert observed.stops[-1].fields['restart_point'].status == 'human_decision_pending'
    assert observed.stops[-1].artifact_references
    git = Mock()
    final = FinalApprovalWorkflowUseCase(git, c.case.flow.repo, c.case.repository, JsonMergeRetryRepository)
    assert not final.start(result, c.case.flow.tmp_path / 'final').success
    git.merge.assert_not_called()


def test_mvp_early_stop_does_not_execute_correction_or_invent_human_decision(correction_flow):
    from application.correction_continuation import ExistingAssessment, EarlyStopCondition
    c = correction_flow
    assessment = ExistingAssessment(EarlyStopCondition.SPECIFICATION_UNCERTAINTY, True,
        'Existing Review requires Specification judgment', ('review.report.problem',))
    stopped = c.c.use_case.correct(c.first, CorrectionStepInput(c.first.review.classification,
        (assessment,), c.problems, c.retest))
    assert stopped.waiting_for_human and stopped.continuation.decision == 'STOPPED'
    c.adapter.run.assert_not_called()
    observed = trace(c.c.case.flow, (*review_outputs(c.first), stopped))
    assert observed.success and not observed.completed, observed.diagnostics
    assert observed.waiting == ('REVIEW_HUMAN_HANDOFF',)
    assert observed.stops[-1].fields['restart_point'].status == 'human_decision_pending'
    assert observed.stops[-1].reason == stopped.handoff.reason
    assert c.target4.collection.evidence_path.is_file()


def test_mvp_correction_limit_handoff_cannot_enter_final_approval(correction_flow):
    c = correction_flow
    # Boundary fixture, not a claim that this test executed three cycles.
    # Count/history validation and increment are covered by correction_continuation,
    # correction_cycle and review_workflow regressions; the main E2E runs a cycle.
    stopped = c.c.use_case._finish(c.c.use_case._route(replace(c.first, correction_count=3)))
    assert stopped.waiting_for_human and stopped.continuation.decision == 'STOPPED'
    assert any(r.code == 'MAX_CORRECTION_COUNT_REACHED' for r in stopped.continuation.reasons)
    c.adapter.run.assert_not_called()
    git = Mock()
    final = FinalApprovalWorkflowUseCase(git, c.c.case.flow.repo, c.c.case.repository, JsonMergeRetryRepository)
    rejected = final.start(stopped, c.c.case.flow.tmp_path / 'limit_final')
    assert not rejected.success and not rejected.completed
    git.merge.assert_not_called()
    observed = trace(c.c.case.flow, (*review_outputs(c.first), stopped))
    assert observed.success and not observed.completed, observed.diagnostics
    assert observed.waiting == ('REVIEW_HUMAN_HANDOFF',)
    assert observed.stops[-1].fields['restart_point'].status == 'human_decision_pending'


@pytest.mark.parametrize('failure', ['missing_human', 'changed_target', 'dirty', 'dirty_at_execution',
    'merge', 'verification', 'partial_history'])
def test_mvp_final_gate_failures_never_become_successful_completion(final_case, monkeypatch, failure):
    c, git, final, review, waiting = final_case
    configure_merge(final_case)
    if failure == 'changed_target':
        waiting.target.request.artifact_path.write_text('{}')
    elif failure == 'dirty':
        git.get_state.return_value = replace(git.get_state.return_value, git_status=' M source.py')
    elif failure == 'dirty_at_execution':
        clean = git.get_state.return_value
        git.get_state.side_effect = [clean, replace(clean, git_status=' M source.py')]
    elif failure == 'merge':
        git.merge.return_value = replace(git.merge.return_value, returncode=1, errors=('Injected merge error',))
    elif failure == 'verification':
        git.verify_merge.return_value = replace(git.verify_merge.return_value, content_matched=False)
    elif failure == 'partial_history':
        monkeypatch.setattr('application.state_transition.save_state_transition_history',
            Mock(side_effect=OSError('History storage unavailable')))
    result = final.resume(waiting.snapshot_path, None if failure == 'missing_human' else approve())
    observed = trace(c.case.flow, (*review_outputs(review), waiting, result))
    assert not result.completed and not observed.completed
    assert observed.current_state == result.current_state
    assert observed.stops[-1].fields['restart_point'].status == 'human_decision_pending'
    if failure == 'missing_human':
        assert result.waiting_for_human and result.approval is None
        assert observed.waiting == ('FINAL_APPROVAL',)
    else:
        assert not result.success and not observed.success
        assert observed.stops[-1].reason == result.stop_reason
    if failure in ('missing_human', 'changed_target', 'dirty', 'dirty_at_execution'):
        git.merge.assert_not_called()
    if failure == 'dirty_at_execution':
        assert result.ready.merge_ready and result.merge.result.failures
    if failure == 'partial_history':
        assert result.merge.result.succeeded
        assert observed.current_state['status'] == 'completed'
        assert any(t.history_status == 'not_saved' for t in observed.transitions)
    else:
        assert observed.current_state['status'] == 'final_approval_pending'


@pytest.mark.parametrize('selection, state', [('Implementation Correction', 'correction_requested'),
    ('Plan Revision', 'final_approval_pending'), ('Specification Reconsideration', 'final_approval_pending'),
    ('Cancellation', 'cancelled')])
def test_mvp_final_human_route_retains_target_without_automatic_destination_execution(final_case, selection, state):
    from application.final_approval_workflow import HumanFinalDecisionInput
    c, git, final, review, waiting = final_case
    result = final.resume(waiting.snapshot_path, HumanFinalDecisionInput(selection, 'Explicit Human return'))
    observed = trace(c.case.flow, (*review_outputs(review), waiting, result))
    assert result.success and observed.success, observed.diagnostics
    assert result.approval is None and not observed.completed
    assert observed.current_state['status'] == state
    assert observed.stops[-1].restart_point == (None if selection == 'Cancellation' else result.routing.destination)
    assert observed.stops[-1].fields['restart_point'].status == ('terminal' if selection == 'Cancellation' else 'known')
    assert waiting.target.request.artifact_path.is_file()
    git.merge.assert_not_called()


@pytest.mark.parametrize('failure', ['merge', 'verification'])
def test_mvp_human_authorized_retry_preserves_approval_evidence_and_correction_count(final_case, failure):
    from application.technical_merge_retry import MergeRetryAuthorization
    c, git, final, review, waiting = final_case
    configure_merge(final_case)
    successful_merge, successful_verification = git.merge.return_value, git.verify_merge.return_value
    if failure == 'merge':
        git.merge.return_value = replace(successful_merge, returncode=1, errors=('Temporary failure',))
    else:
        git.verify_merge.return_value = replace(successful_verification, content_matched=False)
    failed = final.resume(waiting.snapshot_path, approve())
    assert not failed.success and failed.merge.operation_id
    stopped_trace = trace(c.case.flow, (*review_outputs(review), waiting, failed))
    assert stopped_trace.waiting == ('MERGE_RETRY_AUTHORIZATION',)
    assert stopped_trace.stops[-1].fields['restart_point'].status == 'human_decision_pending'
    if failure == 'verification':
        # Merge already succeeded: model the actual post-merge Git facts before
        # asking to repeat verification. Retaining pre-merge facts must fail.
        git.get_state.return_value = successful_verification.repository_state
        git.get_current_head.return_value = successful_verification.current_head
        git.get_branch_head.side_effect = lambda branch: (successful_verification.target_head
            if branch == 'developer' else successful_verification.source_head)
    verification_calls = git.verify_merge.call_count
    denied = final.retry(failed.retry_snapshot_path)
    assert not denied.success
    git.retry_merge.assert_not_called()
    assert git.verify_merge.call_count == verification_calls
    assert any('authorization' in reason for reason in denied.merge.failures)
    before = {p: p.read_bytes() for p in c.case.flow.repo.approvals_dir.glob('*.json')}
    evidence_before = review.request.upstream.collection.evidence_path.read_bytes()
    git.retry_merge.return_value = successful_merge
    git.verify_merge.return_value = successful_verification
    result = final.retry(failed.retry_snapshot_path,
        MergeRetryAuthorization(failed.merge.operation_id, True, 'Human confirms same safe operation'))
    assert result.completed, result.stop_reason
    observed = trace(c.case.flow, (*review_outputs(review), waiting, failed, denied, result))
    assert observed.success and observed.completed, observed.diagnostics
    assert result.merge.operation_id == failed.merge.operation_id
    assert result.merge.retry_count == 1 and review.correction_count == 0
    assert {p: p.read_bytes() for p in before} == before
    assert review.request.upstream.collection.evidence_path.read_bytes() == evidence_before
    git.merge.assert_called_once()
    if failure == 'merge':
        git.retry_merge.assert_called_once()
    else:
        git.retry_merge.assert_not_called()
