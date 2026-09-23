from dataclasses import asdict, replace

import pytest

from application.correction_continuation import ContinuationInput, ContinuationOutput, ContinuationDecision, ContinuationReason
from application.review_result import ReviewResult
from test_correction_continuation import continuation_case
from test_correction_routing import routing_case
from test_classify_review_result import result_case
from test_prepare_review_input import review_case
from test_correction_cycle import cycle_case


@pytest.fixture
def handoff_case(continuation_case):
    c, review, history, runner = continuation_case
    # The current Review Input identifies the new Correction implementation.
    prepared = review.review.prepared
    inp = prepared.review_input
    identity = inp.evidence.identity
    inp = replace(inp, request=replace(inp.request, implementation_id=identity.implementation_id,
                                      evidence_id=identity.evidence_id))
    prepared = replace(prepared, review_input=inp, acquired=inp)
    reviewed = replace(review.review, prepared=prepared, batch=replace(review.review.batch, prepared=prepared))
    review = replace(review, review=reviewed, result=ReviewResult.HUMAN_REVIEW_REQUIRED,
                     report=replace(review.report, proposed_result=ReviewResult.HUMAN_REVIEW_REQUIRED,
                                    human_questions=('Clarify the required behavior before continuing.',)))
    continuation = ContinuationOutput(ContinuationInput(review, 3, (history,)), ContinuationDecision.STOPPED,
        (ContinuationReason('HUMAN_REVIEW_REQUIRED', 'The existing Review requires Human judgment.', ('review.report',)),))
    return c, continuation, identity.implementation_id, runner


def test_prepares_human_review_handoff_preserving_result_evidence_and_history_without_human_decision(handoff_case):
    from application.review_handoff import ReviewHandoffInput, HandoffType
    from application.prepare_review_handoff import PrepareReviewHandoffUseCase

    c, continuation, identity, runner = handoff_case
    request = ReviewHandoffInput(continuation, identity, 'reviewing')
    snapshot = asdict(request)
    disk = {p: p.read_bytes() for p in c['request'].repository_path.rglob('*') if p.is_file()}
    output = PrepareReviewHandoffUseCase().execute(request)
    assert output.handoff_type == HandoffType.HUMAN_REVIEW
    assert output.human_judgment_required
    assert output.required_human_action == continuation.request.review.report.human_questions
    assert output.reason
    assert not output.failures
    assert output.current_state == 'reviewing'
    assert output.request is request
    assert output.request.continuation is continuation
    assert asdict(request) == snapshot
    assert disk == {p: p.read_bytes() for p in disk}
    assert 'continuation.request.review' in output.artifact_references
    assert 'continuation.request.history' in output.artifact_references
    runner.run.assert_not_called()
    c['repository'].save.assert_not_called()
    c['approvals'].save.assert_not_called()


def handoff_request(case, result=ReviewResult.REVISION_REQUIRED, decision=ContinuationDecision.STOPPED):
    from application.review_handoff import ReviewHandoffInput
    _, continuation, identity, _ = case
    review = continuation.request.review
    report = replace(review.report, proposed_result=result, human_questions=()) if result else None
    review = replace(review, result=result, report=report)
    continuation = replace(continuation, request=replace(continuation.request, review=review), decision=decision,
        reasons=(ContinuationReason('MAX_CORRECTION_COUNT_REACHED', 'Human must judge any further correction; Count is not reset.',
                                    ('correction_count',)),))
    return ReviewHandoffInput(continuation, identity, 'reviewing')


def prepare(request):
    from application.prepare_review_handoff import PrepareReviewHandoffUseCase
    return PrepareReviewHandoffUseCase().execute(request)


def replace_review(request, review):
    return replace(request, continuation=replace(request.continuation,
        request=replace(request.continuation.request, review=review)))


def test_limit_stop_preserves_revision_count_and_reason(handoff_case):
    request = handoff_request(handoff_case)
    output = prepare(request)
    assert output.handoff_type == 'HUMAN_REVIEW'
    assert 'MAX_CORRECTION_COUNT_REACHED' in output.reason
    assert output.required_human_action
    assert output.request.continuation.request.correction_count == 3
    assert output.request.continuation.request.review.result == 'REVISION_REQUIRED'
    assert not output.failures


@pytest.mark.parametrize('failure', ['review_failures', 'execution_error', 'parse_error', 'comparison', 'evidence'])
def test_upstream_undetermined_is_human_handoff_not_target_nine_failure(handoff_case, failure):
    request = handoff_request(handoff_case, None, ContinuationDecision.UNDETERMINED)
    review = request.continuation.request.review
    if failure in ('review_failures', 'execution_error', 'parse_error'):
        review = replace(review, **{failure: ('Upstream failure',) if failure == 'review_failures' else 'Upstream failure'})
    elif failure == 'evidence':
        prepared = review.review.prepared
        prepared = replace(prepared, review_input=None, acquired=replace(prepared.acquired, evidence=None),
                           missing_information=('Evidence unavailable upstream',))
        review = replace(review, review=replace(review.review, prepared=prepared))
    request = replace_review(request, review)
    output = prepare(request)
    assert output.handoff_type == 'HUMAN_REVIEW'
    assert not output.failures
    assert output.unresolved_issues
    assert output.request.continuation.request.review.result is None


@pytest.mark.parametrize('missing', ['continuation', 'identity', 'state', 'reference', 'wrong_identity', 'wrong_state'])
def test_target_nine_input_failure_is_distinct_and_never_ready(handoff_case, missing):
    from uuid import uuid4
    request = handoff_request(handoff_case, ReviewResult.HUMAN_REVIEW_REQUIRED)
    if missing == 'continuation':
        request = replace(request, continuation=None)
    elif missing == 'identity':
        request = replace(request, implementation_id=None)
    elif missing == 'state':
        request = replace(request, current_state=None)
    elif missing == 'reference':
        request = replace(request, required_references=('continuation.request.no_such_artifact',))
    elif missing == 'wrong_identity':
        request = replace(request, implementation_id=uuid4())
    else:
        request = replace(request, current_state='correction_requested')
    output = prepare(request)
    assert output.handoff_type == 'NONE'
    assert output.failures
    assert not output.human_judgment_required
    assert output.request is request


def test_unresolvable_upstream_trigger_reference_is_target_nine_failure(handoff_case):
    request = handoff_request(handoff_case)
    continuation = replace(request.continuation, reasons=(ContinuationReason('STOP', 'Known stop', ('history.999',)),))
    assert prepare(replace(request, continuation=continuation)).failures


def approved_request(case):
    from test_classify_review_result import approved
    from application.review_result import ReviewResultReport
    request = handoff_request(case, ReviewResult.APPROVED, ContinuationDecision.CORRECTION_NOT_NEEDED)
    review = request.continuation.request.review
    data = approved(review.review)
    data['proposed_result'] = ReviewResult(data.pop('result'))
    for field in ('references', 'resolutions', 'targets', 'human_questions', 'unresolved'):
        data[field] = tuple(data[field])
    request = replace_review(request, replace(review, report=ReviewResultReport(**data)))
    return replace(request, continuation=replace(request.continuation,
        reasons=(ContinuationReason('APPROVED', 'No next correction is required.', ('review.result',)),)))


def test_explicit_critical_change_forms_approval_handoff_without_approval(handoff_case):
    from application.review_handoff import CriticalChangeReferences
    request = handoff_request(handoff_case)
    # These references project the content already determined by upstream Review.
    critical = CriticalChangeReferences(
        'continuation.request.review.report.problem', 'continuation.request.review.report.cause',
        'continuation.request.review.report.targets', 'continuation.request.review.report.rationale')
    request = replace(request, critical_change=critical)
    output = prepare(request)
    assert output.handoff_type == 'CRITICAL_CHANGE_APPROVAL'
    assert output.human_judgment_required
    assert output.current_state == 'reviewing'
    assert critical.impact_reference in output.artifact_references
    assert not output.failures


def test_critical_stop_without_required_change_information_is_not_ready(handoff_case):
    request = handoff_request(handoff_case)
    continuation = replace(request.continuation, reasons=(ContinuationReason('CRITICAL_CHANGE', 'Approval is required', ('review.report',)),))
    output = prepare(replace(request, continuation=continuation))
    assert output.failures
    assert output.handoff_type == 'NONE'


def test_approved_with_no_current_unresolved_issues_is_phase_six_ready_without_final_approval(handoff_case):
    request = approved_request(handoff_case)
    snapshot = asdict(request)
    output = prepare(request)
    assert output.handoff_type == 'PHASE_6'
    assert not output.required_human_action
    assert not output.unresolved_issues
    assert not output.failures
    assert output.current_state == 'reviewing'
    assert asdict(request) == snapshot
    assert not hasattr(output, 'head_commit')
    assert 'continuation.request.review.review.prepared.review_input.evidence' in output.artifact_references
    assert 'continuation.request.review.review.prepared.review_input.repository_state' in output.artifact_references
    # Existing findings and mechanical mismatches were resolved by Target 4, not deleted.
    assert request.continuation.request.review.review.batch.aspects[0].findings
    assert request.continuation.request.review.review.prepared.mismatches


@pytest.mark.parametrize('problem', ['review_failure', 'questions', 'unresolved', 'cycle_failure', 'stopped', 'undetermined'])
def test_approved_does_not_override_current_unresolved_issues(handoff_case, problem):
    from application.correction_cycle import CycleFailure
    request = approved_request(handoff_case)
    review = request.continuation.request.review
    if problem == 'review_failure':
        request = replace_review(request, replace(review, review_failures=('Review execution failed',)))
    elif problem in ('questions', 'unresolved'):
        field = 'human_questions' if problem == 'questions' else 'unresolved'
        request = replace_review(request, replace(review, report=replace(review.report, **{field: ('Still requires judgment',)})))
    elif problem == 'cycle_failure':
        history = replace(request.continuation.request.history[-1], failures=(CycleFailure('codex_execution', 'Partial failure'),))
        request = replace(request, continuation=replace(request.continuation,
            request=replace(request.continuation.request, history=(history,))))
    else:
        decision = ContinuationDecision.STOPPED if problem == 'stopped' else ContinuationDecision.UNDETERMINED
        request = replace(request, continuation=replace(request.continuation, decision=decision,
            reasons=(ContinuationReason('UNRESOLVED', 'An upstream issue remains', ('review.report',)),)))
    output = prepare(request)
    assert output.handoff_type == 'HUMAN_REVIEW'
    assert output.unresolved_issues
    assert not output.failures


def test_existing_explicit_resolution_can_clear_a_retained_cycle_failure(handoff_case):
    from application.correction_cycle import CycleFailure
    from application.review_handoff import ExistingIssueResolution
    request = approved_request(handoff_case)
    review = request.continuation.request.review
    review = replace(review, report=replace(review.report, rationale='The earlier partial failure is resolved by verified re-test and re-review.'))
    request = replace_review(request, review)
    history = replace(request.continuation.request.history[-1], failures=(CycleFailure('codex_execution', 'Earlier partial failure'),))
    request = replace(request, continuation=replace(request.continuation,
        request=replace(request.continuation.request, history=(history,))))
    request = replace(request, resolutions=(ExistingIssueResolution(
        'continuation.request.history.0.failures.0', 'continuation.request.review.report.rationale'),))
    output = prepare(request)
    assert output.handoff_type == 'PHASE_6'
    assert output.request.continuation.request.history[0].failures


def test_revision_and_continuation_allowed_returns_none_without_correction(handoff_case):
    request = handoff_request(handoff_case, decision=ContinuationDecision.CONTINUATION_ALLOWED)
    output = prepare(request)
    assert output.handoff_type == 'NONE'
    assert not output.failures
    assert not output.human_judgment_required
    assert not output.required_human_action


@pytest.mark.parametrize('missing', ['report', 'evidence', 'repository', 'history', 'wrong_evidence_id'])
def test_phase_six_requires_its_own_reference_consistency(handoff_case, missing):
    from uuid import uuid4
    request = approved_request(handoff_case)
    review = request.continuation.request.review
    if missing == 'report':
        request = replace_review(request, replace(review, report=None))
    elif missing == 'history':
        request = replace(request, continuation=replace(request.continuation,
            request=replace(request.continuation.request, history=())))
    else:
        prepared = review.review.prepared
        inp = prepared.review_input
        if missing == 'wrong_evidence_id':
            inp = replace(inp, evidence=replace(inp.evidence, identity=replace(inp.evidence.identity, evidence_id=uuid4())))
        else:
            inp = replace(inp, **{'evidence' if missing == 'evidence' else 'repository_state': None})
        prepared = replace(prepared, review_input=inp)
        request = replace_review(request, replace(review, review=replace(review.review, prepared=prepared)))
    output = prepare(request)
    assert output.failures
    assert output.handoff_type == 'NONE'


def test_failed_retry_is_not_hidden_by_approved(handoff_case):
    from uuid import uuid4
    from application.review_retry import ReviewRetryHistory, ReviewAIOperation, ReviewOperationKind, AIExecutionAttempt
    from core.ai.ai_request import AIRequest
    request = approved_request(handoff_case)
    operation = ReviewAIOperation(uuid4(), ReviewOperationKind.BATCH, AIRequest('old request'), request.continuation.request.review.review)
    history = ReviewRetryHistory(operation, AIExecutionAttempt(execution_error='original'), AIExecutionAttempt(execution_error='retry failed'))
    request = replace(request, continuation=replace(request.continuation,
        request=replace(request.continuation.request, retry_history=(history,))))
    assert prepare(request).handoff_type == 'HUMAN_REVIEW'


@pytest.mark.parametrize('invalid', ['missing_input', 'unknown_state', 'unknown_decision', 'bad_resolution', 'old_resolution', 'critical_ref'])
def test_malformed_handoff_input_is_failure_without_fallback(handoff_case, invalid):
    from application.review_handoff import ExistingIssueResolution, CriticalChangeReferences
    request = approved_request(handoff_case)
    if invalid == 'missing_input':
        request = replace(request, continuation=replace(request.continuation, request=None))
    elif invalid == 'unknown_state':
        request = replace(request, current_state='invented_state')
    elif invalid == 'unknown_decision':
        request = replace(request, continuation=replace(request.continuation, decision='invented_decision'))
    elif invalid == 'bad_resolution':
        request = replace(request, resolutions=(ExistingIssueResolution('missing', 'continuation.request.review.report.rationale'),))
    elif invalid == 'old_resolution':
        request = replace(request, unresolved_references=('continuation.request.history.0.routing.request.review.report.problem',),
            resolutions=(ExistingIssueResolution('continuation.request.history.0.routing.request.review.report.problem',
                'continuation.request.history.0.routing.request.review.report.rationale'),))
    else:
        request = replace(request, critical_change=CriticalChangeReferences('missing', 'missing', 'missing', 'missing'))
    output = prepare(request)
    assert output.handoff_type == 'NONE'
    assert output.failures


@pytest.mark.parametrize('kind', ['HUMAN_REVIEW', 'CRITICAL_CHANGE_APPROVAL', 'PHASE_6', 'NONE', 'FAILURE'])
@pytest.mark.parametrize('mode', ['BATCH', 'STAGED'])
def test_every_handoff_is_read_only_without_approval_or_workflow_execution(handoff_case, monkeypatch, kind, mode):
    from unittest.mock import Mock
    from application.review_handoff import CriticalChangeReferences
    from test_classify_review_result import staged
    request = approved_request(handoff_case) if kind == 'PHASE_6' else handoff_request(handoff_case)
    if kind == 'CRITICAL_CHANGE_APPROVAL':
        request = replace(request, critical_change=CriticalChangeReferences(
            'continuation.request.review.report.problem', 'continuation.request.review.report.cause',
            'continuation.request.review.report.targets', 'continuation.request.review.report.rationale'))
    elif kind == 'NONE':
        request = replace(request, continuation=replace(request.continuation, decision=ContinuationDecision.CONTINUATION_ALLOWED))
    elif kind == 'FAILURE':
        request = replace(request, implementation_id=None)
    if mode == 'STAGED':
        review = request.continuation.request.review
        request = replace_review(request, replace(review, review=staged(review.review)))
    snapshot = asdict(request)
    c = handoff_case[0]
    disk = {p: p.read_bytes() for p in c['request'].repository_path.rglob('*') if p.is_file()}
    forbidden = Mock(side_effect=AssertionError('Target 9 must only form a handoff'))
    targets = ('application.state_transition.transition_state',
        'application.current_state_repository.save_current_state',
        'application.state_transition_history.save_state_transition_history',
        'core.approval_record_service.build_approval_record_from_artifact',
        'core.approval_record.build_approval_record', 'core.approval_validation.validate_approval_result',
        'application.prepare_correction.PrepareCorrectionUseCase.execute',
        'application.execute_correction_cycle.ExecuteCorrectionCycleUseCase.execute',
        'application.review_with_retry.ReviewWithRetryUseCase.execute',
        'application.collect_implementation_evidence.CollectImplementationEvidenceUseCase.execute',
        'core.ai.ai_service.AIService.run', 'core.ai.codex_runner.CodexRunner.run',
        'infrastructure.git_repository_state_provider.GitRepositoryStateProvider.get_state', 'subprocess.Popen')
    # Import consumers before replacing their dependencies, so guards cannot leak
    # through module-level aliases into the later real Cycle integration test.
    from application.execute_correction_cycle import ExecuteCorrectionCycleUseCase
    from application.collect_implementation_evidence import CollectImplementationEvidenceUseCase
    from core.approval_record_service import build_approval_record_from_artifact
    for target in targets:
        monkeypatch.setattr(target, forbidden)
    output = prepare(request)
    assert output.handoff_type == ('NONE' if kind == 'FAILURE' else kind)
    assert asdict(request) == snapshot
    assert output.current_state == request.current_state
    assert disk == {p: p.read_bytes() for p in c['request'].repository_path.rglob('*') if p.is_file()}
    forbidden.assert_not_called()
    c['repository'].save.assert_not_called()
    c['approvals'].save.assert_not_called()


def test_upstream_missing_reference_value_is_not_target_nine_reference_failure(handoff_case):
    request = handoff_request(handoff_case, None, ContinuationDecision.UNDETERMINED)
    request = replace(request, continuation=replace(request.continuation,
        reasons=(ContinuationReason('REVIEW_MISSING', 'Review report was not established upstream.', ('review.report',)),)))
    assert prepare(request).handoff_type == 'HUMAN_REVIEW'
    assert not prepare(request).failures


def test_real_cycle_and_continuation_outputs_can_be_handed_off_without_reexecution(cycle_case):
    from application.correction_continuation import ContinuationInput
    from application.evaluate_correction_continuation import EvaluateCorrectionContinuationUseCase
    from application.review_handoff import ReviewHandoffInput
    case = cycle_case
    cycle = case['use_case'].execute(case['request'])
    assert cycle.re_review is not None, cycle.failures
    continuation = EvaluateCorrectionContinuationUseCase().execute(ContinuationInput(
        cycle.re_review.classification, cycle.history.correction_count, (cycle.history,),
        retry_history=cycle.re_review.history))
    request = ReviewHandoffInput(continuation, cycle.history.implementation_id, cycle.current_state, cycle=cycle)
    calls = tuple(case['calls'])
    before = asdict(request)
    output = prepare(request)
    assert output.handoff_type == 'HUMAN_REVIEW'
    assert not output.failures
    assert tuple(case['calls']) == calls
    assert asdict(request) == before
    assert output.request.cycle.history_path == cycle.history_path
    assert output.request.cycle.history.command_trace_path.exists()
    assert output.request.cycle.history.test_execution_record_path.exists()


def test_approved_with_explicit_critical_change_never_becomes_phase_six(handoff_case):
    from application.review_handoff import CriticalChangeReferences
    request = approved_request(handoff_case)
    # Critical facts are explicit upstream input, not inferred from finding text.
    critical = CriticalChangeReferences('continuation.request.review.report.rationale',
        'continuation.request.review.report.rationale',
        'continuation.request.review.review.prepared.review_input.evidence.scope.target_paths',
        'continuation.request.review.report.rationale')
    output = prepare(replace(request, critical_change=critical))
    assert output.handoff_type == 'CRITICAL_CHANGE_APPROVAL'
    assert output.unresolved_issues
    assert output.request.continuation.request.review.result == 'APPROVED'


def test_explicit_pending_upstream_issue_blocks_phase_six(handoff_case):
    request = approved_request(handoff_case)
    ref = 'continuation.request.history.0.routing.request.review.report.problem'
    output = prepare(replace(request, unresolved_references=(ref,)))
    assert output.handoff_type == 'HUMAN_REVIEW'
    assert ref in output.unresolved_issues


@pytest.mark.parametrize('invalid', ['result', 'report_result', 'input_identity'])
def test_handoff_rejects_its_own_identity_and_result_reference_inconsistency(handoff_case, invalid):
    from uuid import uuid4
    request = approved_request(handoff_case)
    review = request.continuation.request.review
    if invalid == 'result':
        review = replace(review, result='INVENTED')
    elif invalid == 'report_result':
        review = replace(review, report=replace(review.report, proposed_result=ReviewResult.REVISION_REQUIRED))
    else:
        prepared = review.review.prepared
        inp = prepared.review_input
        inp = replace(inp, request=replace(inp.request, implementation_id=uuid4()))
        review = replace(review, review=replace(review.review, prepared=replace(prepared, review_input=inp)))
    output = prepare(replace_review(request, review))
    assert output.failures
    assert output.handoff_type == 'NONE'


def test_current_cycle_failure_is_not_discarded_when_other_history_is_clean(cycle_case):
    from application.correction_cycle import CycleFailure
    from application.review_handoff import ReviewHandoffInput
    case = cycle_case
    cycle = case['use_case'].execute(case['request'])
    assert cycle.re_review is not None, cycle.failures
    review = cycle.re_review.classification
    continuation = ContinuationOutput(ContinuationInput(review, cycle.history.correction_count, (cycle.history,)),
        ContinuationDecision.STOPPED, (ContinuationReason('HUMAN_REVIEW_REQUIRED', 'Human judgment required', ('review.report',)),))
    cycle = replace(cycle, failures=(*cycle.failures, CycleFailure('history_persistence', 'History could not be persisted')))
    request = ReviewHandoffInput(continuation, cycle.history.implementation_id, cycle.current_state, cycle=cycle)
    output = prepare(request)
    assert output.handoff_type == 'HUMAN_REVIEW'
    assert 'cycle.failures.0' in output.unresolved_issues
    assert not output.failures


def test_formally_recorded_upstream_history_uncertainty_remains_human_handoff(handoff_case):
    request = handoff_request(handoff_case, None, ContinuationDecision.UNDETERMINED)
    request = replace(request, continuation=replace(request.continuation,
        request=replace(request.continuation.request, history=()),
        reasons=(ContinuationReason('HISTORY_UNAVAILABLE', 'Required comparison history is unavailable upstream.', ('history',)),)))
    output = prepare(request)
    assert output.handoff_type == 'HUMAN_REVIEW'
    assert not output.failures
    assert output.request.continuation.request.history == ()


@pytest.mark.parametrize('missing', ['report', 'reason'])
def test_established_human_result_requires_its_report_and_stop_reason(handoff_case, missing):
    request = handoff_request(handoff_case, ReviewResult.HUMAN_REVIEW_REQUIRED)
    if missing == 'report':
        request = replace_review(request, replace(request.continuation.request.review, report=None))
    else:
        request = replace(request, continuation=replace(request.continuation, reasons=()))
    output = prepare(request)
    assert output.failures
    assert output.handoff_type == 'NONE'


def test_old_issues_within_prior_review_do_not_block_current_approved_result(handoff_case):
    request = approved_request(handoff_case)
    old_review = request.continuation.request.history[0].routing.request.review
    assert old_review.result == 'REVISION_REQUIRED'
    assert old_review.review.batch.aspects[0].findings
    assert prepare(request).handoff_type == 'PHASE_6'


def test_phase_six_handoff_references_resolve_without_head_substitution(handoff_case):
    from application.evaluate_correction_continuation import _resolve
    request = approved_request(handoff_case)
    output = prepare(request)
    for ref in output.artifact_references:
        assert _resolve(output.request, ref) is not None
    assert not any('head_commit' in ref for ref in output.artifact_references)
    assert output.request.continuation.request.review.review.prepared.review_input.evidence.identity.base_commit
