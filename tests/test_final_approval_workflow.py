from unittest.mock import Mock
from dataclasses import replace
import json
from pathlib import Path
import pytest
from infrastructure.json_merge_retry_repository import JsonMergeRetryRepository

from test_plan_workflow import flow
from test_implementation_workflow import implementation
from test_evidence_workflow import evidence_flow
from test_review_workflow import review_flow, correction_flow


@pytest.fixture
def review_ready(review_flow):
    from application.final_approval_workflow import FinalApprovalWorkflowUseCase
    c = review_flow
    upstream = c.use_case.start(c.request)
    assert upstream.ready_for_final_approval
    git = Mock()
    git.get_state.return_value = upstream.review.review.prepared.review_input.repository_state
    git.get_current_head.return_value = 'a' * 40
    workflow = FinalApprovalWorkflowUseCase(git, c.case.flow.repo, c.case.repository, JsonMergeRetryRepository)
    return c, git, workflow, upstream


@pytest.fixture
def final_case(review_ready):
    c, git, workflow, upstream = review_ready
    output = workflow.start(upstream, c.case.flow.tmp_path / 'final')
    assert output.success, output.stop_reason
    return c, git, workflow, upstream, output


def test_phase6_workflow_waits_for_human_final_approval(final_case):
    c, git, workflow, upstream, output = final_case
    assert output.success, output.stop_reason
    assert output.waiting_for_human
    assert output.current_state['status'] == 'final_approval_pending'
    assert output.target.succeeded
    assert output.snapshot_path.is_file()
    git.merge.assert_not_called()


def test_saved_snapshot_resumes_to_verified_completion_without_reentering(final_case, monkeypatch):
    from application.final_approval_workflow import FinalApprovalWorkflowUseCase, HumanFinalDecisionInput
    from application.git_merge_service import GitMergeResult, GitMergeVerification
    c, git, workflow, upstream, waiting = final_case
    source = waiting.target.artifact.implementation_branch
    state = replace(git.get_state.return_value, git_status='')
    git.get_state.return_value = state
    git.get_branch_head.side_effect = lambda branch: 'a' * 40 if branch == source else 'd' * 40
    git.get_pending_operations.return_value = ()
    git.get_repository_identity.return_value = 'test-repository'
    git.merge.return_value = GitMergeResult('test-repository', source, 'developer', 'a' * 40, 'd' * 40,
        post_commit='b' * 40, command_started=True, returncode=0)
    git.verify_merge.return_value = GitMergeVerification(replace(state, branch='developer'),
        'b' * 40, 'b' * 40, 'a' * 40, (), True, (), 'tree', 'tree', True, True)
    monkeypatch.setattr('application.final_approval_entry.FinalApprovalEntryUseCase.execute',
        Mock(side_effect=AssertionError('Do not re-enter after restart')))
    restarted = FinalApprovalWorkflowUseCase(git, c.case.flow.repo, c.case.repository, JsonMergeRetryRepository)
    result = restarted.resume(waiting.snapshot_path, HumanFinalDecisionInput(
        'Final Approval', 'Human accepted this target', 'final-1', '2026-09-28T10:00:00+09:00', 'Approved'))
    assert result.success and result.completed, result.stop_reason
    assert result.current_state['status'] == 'completed'
    assert result.target == waiting.target
    assert result.approval.saved and result.approval.approval_valid
    assert result.merge.result.operation.command_success
    assert result.merge.result.verification.verified
    git.merge.assert_called_once()
    git.verify_merge.assert_called_once()


def configure_merge(final_case):
    from application.git_merge_service import GitMergeResult, GitMergeVerification
    c, git, workflow, upstream, waiting = final_case
    source = waiting.target.artifact.implementation_branch
    state = replace(git.get_state.return_value, git_status='')
    git.get_state.return_value = state
    git.get_branch_head.side_effect = lambda branch: 'a' * 40 if branch == source else 'd' * 40
    git.get_pending_operations.return_value = ()
    git.get_repository_identity.return_value = 'test-repository'
    git.merge.return_value = GitMergeResult('test-repository', source, 'developer', 'a' * 40, 'd' * 40,
        post_commit='b' * 40, command_started=True, returncode=0)
    git.verify_merge.return_value = GitMergeVerification(replace(state, branch='developer'),
        'b' * 40, 'b' * 40, 'a' * 40, (), True, (), 'tree', 'tree', True, True)


def approve():
    from application.final_approval_workflow import HumanFinalDecisionInput
    return HumanFinalDecisionInput('Final Approval', 'Human accepted this target',
        'final-1', '2026-09-28T10:00:00+09:00', 'Approved')


def test_restart_retry_uses_persistent_operation_and_only_one_slot(final_case):
    from application.final_approval_workflow import FinalApprovalWorkflowUseCase
    from application.technical_merge_retry import MergeRetryAuthorization
    c, git, workflow, upstream, waiting = final_case
    configure_merge(final_case)
    successful = git.merge.return_value
    git.merge.return_value = replace(successful, returncode=1, errors=('Temporary Git failure',))
    initial = workflow.resume(waiting.snapshot_path, approve())
    assert not initial.success and initial.merge.operation_id
    assert initial.retry_snapshot_path.is_file()
    restarted = FinalApprovalWorkflowUseCase(git, c.case.flow.repo, c.case.repository, JsonMergeRetryRepository)
    unauthorized = restarted.retry(initial.retry_snapshot_path)
    assert not unauthorized.success
    git.retry_merge.assert_not_called()
    git.retry_merge.return_value = successful
    result = restarted.retry(initial.retry_snapshot_path,
        MergeRetryAuthorization(initial.merge.operation_id, True, 'Human confirmed same safe operation'))
    assert result.completed, result.stop_reason
    assert result.merge.retry_count == 1
    git.merge.assert_called_once()
    git.retry_merge.assert_called_once()
    again = FinalApprovalWorkflowUseCase(git, c.case.flow.repo, c.case.repository, JsonMergeRetryRepository).retry(initial.retry_snapshot_path)
    assert not again.success
    git.retry_merge.assert_called_once()


@pytest.mark.parametrize('bad', ['failed', 'stopped', 'handoff', 'review', 'state', 'snapshot_missing', 'snapshot_changed', 'evidence_changed'])
def test_invalid_target_five_never_enters_final_approval(review_ready, bad):
    c, git, workflow, upstream = review_ready
    if bad == 'failed':
        upstream = replace(upstream, success=False)
    elif bad == 'stopped':
        upstream = replace(upstream, stop_reason='Upstream persistence failure')
    elif bad == 'handoff':
        upstream = replace(upstream, handoff=replace(upstream.handoff, handoff_type='HUMAN_REVIEW'))
    elif bad == 'review':
        upstream = replace(upstream, review=replace(upstream.review, classification=None))
    elif bad == 'state':
        c.case.flow.state.write_text('{"status":"cancelled"}')
    elif bad == 'snapshot_missing':
        upstream.artifact_paths[-1].unlink()
    elif bad == 'snapshot_changed':
        upstream.artifact_paths[-1].write_text('{}')
    else:
        c.upstream.collection.evidence_path.write_text('{}')
    before = c.case.flow.state.read_bytes()
    result = workflow.start(upstream, c.case.flow.tmp_path / 'final')
    assert not result.success and result.stop_reason
    assert c.case.flow.state.read_bytes() == before
    git.get_current_head.assert_not_called()
    git.merge.assert_not_called()


@pytest.mark.parametrize('part', ['state', 'history'])
def test_entry_partial_persistence_is_not_waiting(review_ready, monkeypatch, part):
    c, git, workflow, upstream = review_ready
    name = 'save_current_state' if part == 'state' else 'save_state_transition_history'
    monkeypatch.setattr('application.state_transition.' + name, Mock(side_effect=OSError('disk full')))
    result = workflow.start(upstream, c.case.flow.tmp_path / 'final')
    assert not result.success and not result.waiting_for_human
    assert result.current_state['status'] == ('reviewing' if part == 'state' else 'final_approval_pending')
    assert result.target.request.entry.transition
    git.merge.assert_not_called()


@pytest.mark.parametrize('bad', ['missing', 'broken', 'hash', 'identity'])
def test_invalid_waiting_snapshot_stops_without_git(final_case, bad):
    c, git, workflow, upstream, waiting = final_case
    path = waiting.snapshot_path
    if bad == 'missing':
        path.unlink()
    elif bad == 'broken':
        path.write_text('{')
    else:
        data = json.loads(path.read_text(encoding='utf-8'))
        if bad == 'hash':
            data['sha256'] = '0' * 64
        else:
            data['payload']['data']['artifact']['head_commit'] = 'changed'
        path.write_text(json.dumps(data), encoding='utf-8')
    result = workflow.resume(path, approve())
    assert not result.success and result.stop_reason
    git.merge.assert_not_called()


@pytest.mark.parametrize('field', ['artifact_path', 'implementation_evidence_reference', 'git_diff_reference', 'review_report_reference'])
def test_changed_approved_reference_stops_before_record_or_merge(final_case, field):
    c, git, workflow, upstream, waiting = final_case
    path = getattr(waiting.target.request, field)
    path.write_bytes(path.read_bytes() + b' ')
    # Evidence is semantically compared; change its content, not only whitespace.
    if field == 'implementation_evidence_reference':
        path.write_text('{}')
    result = workflow.resume(waiting.snapshot_path, approve())
    assert not result.success and result.stop_reason
    assert result.approval is None
    git.merge.assert_not_called()


@pytest.mark.parametrize('selection,state,destination', [
    ('Implementation Correction', 'correction_requested', 'Codex再実装工程'),
    ('Plan Revision', 'final_approval_pending', 'Plan修正工程'),
    ('Specification Reconsideration', 'final_approval_pending', 'Specification策定工程'),
    ('Cancellation', 'cancelled', 'cancelled'),
])
def test_explicit_nonapproval_routes_do_not_execute_destination(final_case, selection, state, destination):
    from application.final_approval_workflow import HumanFinalDecisionInput
    c, git, workflow, upstream, waiting = final_case
    result = workflow.resume(waiting.snapshot_path, HumanFinalDecisionInput(selection, 'Explicit Human reason'))
    assert result.success, result.stop_reason
    assert result.routing.destination == destination
    assert result.current_state['status'] == state
    assert not result.completed and result.approval is None
    git.merge.assert_not_called()


@pytest.mark.parametrize('selection', [None, 'pending', 'reject', 'APPROVED', 'CRITICAL_CHANGE_APPROVAL'])
def test_missing_or_ambiguous_decision_is_never_approval(final_case, selection):
    from application.final_approval_workflow import HumanFinalDecisionInput
    c, git, workflow, upstream, waiting = final_case
    result = workflow.resume(waiting.snapshot_path, HumanFinalDecisionInput(selection, 'reason'))
    assert result.waiting_for_human is (selection is None)
    assert result.success is (selection is None)
    assert result.approval is None and not result.completed
    git.merge.assert_not_called()


@pytest.mark.parametrize('bad', ['dirty', 'head', 'pending', 'unknown', 'diff', 'destination'])
def test_repository_must_be_safe_independently_of_valid_approval(final_case, bad):
    c, git, workflow, upstream, waiting = final_case
    configure_merge(final_case)
    if bad == 'dirty':
        git.get_state.return_value = replace(git.get_state.return_value, git_status=' M source.py')
    elif bad == 'head':
        git.get_current_head.return_value = 'changed'
    elif bad == 'pending':
        git.get_pending_operations.return_value = ('MERGE_HEAD',)
    elif bad == 'unknown':
        git.get_pending_operations.side_effect = OSError('unavailable')
    elif bad == 'diff':
        git.get_state.return_value = replace(git.get_state.return_value, git_diff='changed')
    else:
        git.get_branch_head.return_value = None
        git.get_branch_head.side_effect = None
    result = workflow.resume(waiting.snapshot_path, approve())
    assert not result.success and not result.completed
    assert result.approval.approval_valid
    assert result.ready.failures
    git.merge.assert_not_called()


@pytest.mark.parametrize('bad', ['command', 'content', 'reverted'])
def test_merge_and_content_verification_are_separate_completion_conditions(final_case, bad):
    c, git, workflow, upstream, waiting = final_case
    configure_merge(final_case)
    if bad == 'command':
        git.merge.return_value = replace(git.merge.return_value, returncode=1)
    elif bad == 'content':
        git.verify_merge.return_value = replace(git.verify_merge.return_value, content_matched=False)
    else:
        git.verify_merge.return_value = replace(git.verify_merge.return_value, approved_content_retained=False)
    result = workflow.resume(waiting.snapshot_path, approve())
    assert not result.success and not result.completed
    assert result.current_state['status'] == 'final_approval_pending'
    assert result.merge.result.operation.command_success is (bad != 'command')
    git.merge.assert_called_once()


def test_completion_history_failure_preserves_completed_state_but_not_success(final_case, monkeypatch):
    import application.state_transition as transitions
    c, git, workflow, upstream, waiting = final_case
    configure_merge(final_case)
    monkeypatch.setattr(transitions, 'save_state_transition_history', Mock(side_effect=OSError('History unavailable')))
    result = workflow.resume(waiting.snapshot_path, approve())
    assert not result.success and not result.completed
    assert result.current_state['status'] == 'completed'
    assert result.completion.failures
    assert result.merge.result.succeeded


def test_latest_correction_evidence_roundtrips_without_initial_evidence_reuse(correction_flow):
    from application.review_workflow import CorrectionStepInput
    from application.final_approval_workflow import FinalApprovalWorkflowUseCase
    c = correction_flow
    upstream = c.c.use_case.correct(c.first, CorrectionStepInput(c.first.review.classification,
        c.assessments, c.problems, c.retest))
    assert upstream.ready_for_final_approval
    git = Mock()
    git.get_state.return_value = upstream.review.review.prepared.review_input.repository_state
    git.get_current_head.return_value = 'a' * 40
    workflow = FinalApprovalWorkflowUseCase(git, c.c.case.flow.repo, c.c.case.repository, JsonMergeRetryRepository)
    waiting = workflow.start(upstream, c.c.case.flow.tmp_path / 'final')
    assert waiting.success, waiting.stop_reason
    restored = workflow.resume(waiting.snapshot_path)
    assert restored.waiting_for_human, restored.stop_reason
    assert restored.target == waiting.target
    assert restored.target.request.implementation_evidence_reference == upstream.cycles[-1].evidence.evidence_path
    assert restored.target.request.implementation_evidence_reference != c.target4.collection.evidence_path
    git.merge.assert_not_called()


@pytest.mark.parametrize('part', ['snapshot', 'receipt', 'ready'])
def test_persistence_failure_never_starts_merge(final_case, monkeypatch, part):
    from application.final_approval_workflow import FinalApprovalWorkflowUseCase
    c, git, workflow, upstream, waiting = final_case
    configure_merge(final_case)
    original = Path.open
    def fail(path, *args, **kwargs):
        suffix = '.decision.json' if part == 'receipt' else '.ready.json'
        if str(path).endswith(suffix) and args and 'x' in args[0]:
            raise OSError('No space')
        return original(path, *args, **kwargs)
    if part == 'snapshot':
        waiting.snapshot_path.write_text('{}')
    else:
        monkeypatch.setattr(Path, 'open', fail)
    result = FinalApprovalWorkflowUseCase(git, c.case.flow.repo, c.case.repository, JsonMergeRetryRepository).resume(waiting.snapshot_path, approve())
    assert not result.success and result.stop_reason
    git.merge.assert_not_called()


@pytest.mark.parametrize('part', ['save', 'reload'])
def test_approval_save_and_reload_failures_do_not_merge(final_case, monkeypatch, part):
    c, git, workflow, upstream, waiting = final_case
    configure_merge(final_case)
    if part == 'save':
        monkeypatch.setattr(c.case.flow.repo, 'save', Mock(side_effect=OSError('Cannot save')))
    else:
        original = c.case.flow.repo.get
        def get(identity):
            record = original(identity)
            return dict(record, artifact_hash='changed') if identity == 'final-1' else record
        monkeypatch.setattr(c.case.flow.repo, 'get', get)
    result = workflow.resume(waiting.snapshot_path, approve())
    assert not result.success and not result.approval.approval_valid
    assert result.approval.saved is (part == 'reload')
    git.merge.assert_not_called()


@pytest.mark.parametrize('bad', ['empty_id', 'existing_id'])
def test_approval_metadata_cannot_overwrite_existing_approval(final_case, bad):
    c, git, workflow, upstream, waiting = final_case
    configure_merge(final_case)
    records = {p: p.read_bytes() for p in c.case.flow.repo.approvals_dir.glob('*.json')}
    identity = '' if bad == 'empty_id' else next(iter(records)).stem
    result = workflow.resume(waiting.snapshot_path, replace(approve(), approval_id=identity))
    assert not result.success and result.stop_reason
    assert {p: p.read_bytes() for p in records} == records
    git.merge.assert_not_called()


def test_retry_verification_after_restart_never_remerges(final_case):
    from application.final_approval_workflow import FinalApprovalWorkflowUseCase
    from application.technical_merge_retry import MergeRetryAuthorization
    c, git, workflow, upstream, waiting = final_case
    configure_merge(final_case)
    good = git.verify_merge.return_value
    git.verify_merge.return_value = replace(good, content_matched=False)
    failed = workflow.resume(waiting.snapshot_path, approve())
    assert not failed.completed
    git.get_state.return_value = good.repository_state
    git.get_current_head.return_value = good.current_head
    git.get_branch_head.side_effect = lambda branch: good.target_head if branch == 'developer' else good.source_head
    git.verify_merge.return_value = good
    result = FinalApprovalWorkflowUseCase(git, c.case.flow.repo, c.case.repository, JsonMergeRetryRepository).retry(failed.retry_snapshot_path,
        MergeRetryAuthorization(failed.merge.operation_id, True, 'Human authorizes same verification'))
    assert result.completed, result.stop_reason
    git.merge.assert_called_once()
    git.retry_merge.assert_not_called()
    assert git.verify_merge.call_count == 2


@pytest.mark.parametrize('bad', ['missing_history', 'unknown_slot', 'attempt_without_result', 'foreign_authorization', 'changed_identity'])
def test_retry_unknown_or_changed_operation_never_reexecutes(final_case, bad):
    from application.final_approval_workflow import FinalApprovalWorkflowUseCase
    from application.technical_merge_retry import MergeRetryAuthorization
    c, git, workflow, upstream, waiting = final_case
    configure_merge(final_case)
    git.merge.return_value = replace(git.merge.return_value, returncode=1, errors=('failure',))
    failed = workflow.resume(waiting.snapshot_path, approve())
    identity = failed.merge.operation_id
    directory = waiting.snapshot_path.parent / 'retry_history' / identity
    authorization = MergeRetryAuthorization(identity, True, 'Human confirmed safe re-execution')
    if bad == 'missing_history':
        (directory / 'initial.json').unlink()
    elif bad == 'unknown_slot':
        path = directory / 'initial.json'
        data = json.loads(path.read_text())
        data['slot'] = 'unknown'
        path.write_text(json.dumps(data))
    elif bad == 'attempt_without_result':
        (directory / 'attempt.json').write_text('{"slot":"consumed"}')
    elif bad == 'foreign_authorization':
        authorization = replace(authorization, operation_id='foreign-operation')
    else:
        git.get_current_head.return_value = 'changed'
    result = FinalApprovalWorkflowUseCase(git, c.case.flow.repo, c.case.repository, JsonMergeRetryRepository).retry(failed.retry_snapshot_path, authorization)
    assert not result.success and not result.completed
    git.merge.assert_called_once()
    git.retry_merge.assert_not_called()


def test_replaying_human_decision_does_not_overwrite_or_remerge(final_case):
    c, git, workflow, upstream, waiting = final_case
    configure_merge(final_case)
    git.merge.return_value = replace(git.merge.return_value, returncode=1, errors=('failure',))
    failed = workflow.resume(waiting.snapshot_path, approve())
    assert not failed.success
    record = c.case.flow.repo.get('final-1')
    again = workflow.resume(waiting.snapshot_path, approve())
    assert not again.success
    assert c.case.flow.repo.get('final-1') == record
    git.merge.assert_called_once()


@pytest.mark.parametrize('diverged', [False, True])
def test_real_git_integration_merges_only_in_disposable_repository(evidence_flow, diverged):
    from application.final_approval_workflow import FinalApprovalWorkflowUseCase
    from application.review_workflow import ReviewWorkflowInput, ReviewWorkflowUseCase
    from application.review_with_retry import ReviewWithRetryUseCase
    from application.review_retry import RetryAuthorization
    from infrastructure.git_cli_merge_service import GitCliMergeService
    from infrastructure.git_repository_state_provider import GitRepositoryStateProvider
    from infrastructure.json_test_state_provider import JsonTestStateProvider
    from core.ai.ai_response import AIResponse
    from core.ai.ai_service import AIService
    from test_review_workflow import approved_response
    from test_review_implementation import response
    from test_git_repository_state_provider import run_git
    c = evidence_flow
    root = c.request.repository
    # Only this pytest-created repository is committed / merged.
    run_git(root, 'commit', '-m', 'Test fixture implementation')
    source_commit = run_git(root, 'rev-parse', 'HEAD')
    if diverged:
        run_git(root, 'checkout', 'developer')
        (root / 'independent.txt').write_text('developer content\n')
        run_git(root, 'add', 'independent.txt')
        run_git(root, 'commit', '-m', 'Test fixture independent change')
        run_git(root, 'checkout', c.request.implementation_branch)
    upstream = c.use_case.execute(c.evidence_request)
    assert upstream.success, upstream.stop_reason
    runner = Mock()
    runner.run.side_effect = lambda request: (approved_response(request)
        if request.prompt.startswith('# Review Result Evaluation') else AIResponse(json.dumps(response()), True))
    reviews = ReviewWorkflowUseCase(c.flow.repo, c.repository, GitRepositoryStateProvider, JsonTestStateProvider,
        ReviewWithRetryUseCase(AIService(runner), lambda *args: RetryAuthorization()))
    reviewed = reviews.start(ReviewWorkflowInput(upstream, 'BATCH', c.flow.tmp_path / 'reviews'))
    assert reviewed.ready_for_final_approval, reviewed.stop_reason
    workflow = FinalApprovalWorkflowUseCase(GitCliMergeService(root), c.flow.repo, c.repository, JsonMergeRetryRepository)
    waiting = workflow.start(reviewed, c.flow.tmp_path / 'final')
    assert waiting.waiting_for_human, waiting.stop_reason
    result = FinalApprovalWorkflowUseCase(GitCliMergeService(root), c.flow.repo, c.repository, JsonMergeRetryRepository).resume(waiting.snapshot_path, approve())
    assert result.completed, result.stop_reason
    assert run_git(root, 'branch', '--show-current') == 'developer'
    assert run_git(root, 'rev-parse', c.request.implementation_branch) == source_commit
    assert (root / 'source.py').read_text() == 'value = 1\n'
    assert result.merge.result.verification.content_matched
    assert result.merge.result.verification.approved_content_retained
    if diverged:
        assert (root / 'independent.txt').read_text() == 'developer content\n'


def test_failed_retry_remains_consumed_after_another_restart(final_case):
    from application.final_approval_workflow import FinalApprovalWorkflowUseCase
    from application.technical_merge_retry import MergeRetryAuthorization
    c, git, workflow, upstream, waiting = final_case
    configure_merge(final_case)
    git.merge.return_value = replace(git.merge.return_value, returncode=1, errors=('failure',))
    git.retry_merge.return_value = git.merge.return_value
    failed = workflow.resume(waiting.snapshot_path, approve())
    first = workflow.retry(failed.retry_snapshot_path,
        MergeRetryAuthorization(failed.merge.operation_id, True, 'Human authorized one retry'))
    assert not first.success and first.merge.retry_count == 1
    again = FinalApprovalWorkflowUseCase(git, c.case.flow.repo, c.case.repository, JsonMergeRetryRepository).retry(failed.retry_snapshot_path)
    assert not again.success and again.merge.retry_count == 1
    assert again.current_state['status'] == 'final_approval_pending'
    git.retry_merge.assert_called_once()


def test_start_snapshot_save_failure_retains_target_and_pending_state(review_ready, monkeypatch):
    c, git, workflow, upstream = review_ready
    monkeypatch.setattr('application.final_approval_workflow.save_checkpoint', Mock(side_effect=OSError('disk full')))
    result = workflow.start(upstream, c.case.flow.tmp_path / 'final')
    assert not result.success and not result.waiting_for_human
    assert result.target.succeeded and result.target.request.artifact_path.is_file()
    assert result.current_state['status'] == 'final_approval_pending'
    git.merge.assert_not_called()


def test_state_change_during_waiting_persistence_is_not_success(review_ready, monkeypatch):
    import application.final_approval_workflow as module
    c, git, workflow, upstream = review_ready
    original = module.save_checkpoint
    def save(path, target):
        original(path, target)
        c.case.flow.state.write_text('{"status":"cancelled"}')
    monkeypatch.setattr(module, 'save_checkpoint', save)
    result = workflow.start(upstream, c.case.flow.tmp_path / 'final')
    assert not result.success and not result.waiting_for_human
    assert result.current_state['status'] == 'cancelled'
    git.merge.assert_not_called()


def test_waiting_result_save_failure_is_not_normal_waiting(final_case, monkeypatch):
    c, git, workflow, upstream, waiting = final_case
    monkeypatch.setattr(workflow, '_save_event', Mock(side_effect=OSError('Cannot save result')))
    result = workflow.resume(waiting.snapshot_path)
    assert not result.success and not result.waiting_for_human
    assert result.stop_reason and result.current_state['status'] == 'final_approval_pending'
    git.merge.assert_not_called()


def test_resumed_waiting_observes_external_state_change(final_case, monkeypatch):
    c, git, workflow, upstream, waiting = final_case
    original = workflow._validate_target
    def validate(target):
        original(target)
        c.case.flow.state.write_text('{"status":"cancelled"}')
    monkeypatch.setattr(workflow, '_validate_target', validate)
    result = workflow.resume(waiting.snapshot_path)
    assert not result.success and not result.waiting_for_human
    assert result.current_state['status'] == 'cancelled'
    git.merge.assert_not_called()
