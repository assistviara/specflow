from dataclasses import asdict, replace
from uuid import uuid4

import pytest

from application.correction_cycle import CorrectionHistory
from application.correction_routing import CorrectionRoutingOutput
from test_correction_routing import routing_case
from test_classify_review_result import result_case
from test_prepare_review_input import review_case


@pytest.fixture
def continuation_case(routing_case):
    c, routing, runner = routing_case
    previous = routing.review
    old = previous.review.prepared.review_input.evidence
    identity = uuid4()
    new = replace(old, identity=replace(old.identity, implementation_id=identity,
        evidence_id=uuid4(), implementation_kind='CORRECTION', previous_evidence_id=old.identity.evidence_id))
    prepared = previous.review.prepared
    inp = replace(prepared.review_input, evidence=new)
    prepared = replace(prepared, review_input=inp, acquired=inp)
    reviewed = replace(previous.review, prepared=prepared, batch=replace(previous.review.batch, prepared=prepared))
    current = replace(previous, review=reviewed)
    history = CorrectionHistory(identity, CorrectionRoutingOutput(routing), old.identity.evidence_id,
                                2, 3, changed_files=('source.py',), new_evidence_id=new.identity.evidence_id)
    return c, current, history, runner


def test_stops_next_correction_at_count_three_preserving_review_and_history(continuation_case):
    from application.correction_continuation import ContinuationInput, ContinuationDecision
    from application.evaluate_correction_continuation import EvaluateCorrectionContinuationUseCase

    c, review, history, runner = continuation_case
    request = ContinuationInput(review, 3, (history,))
    before = asdict(request)
    disk = {p: p.read_bytes() for p in c['request'].repository_path.rglob('*') if p.is_file()}
    output = EvaluateCorrectionContinuationUseCase().execute(request)
    assert output.decision == ContinuationDecision.STOPPED
    assert output.reasons[0].code == 'MAX_CORRECTION_COUNT_REACHED'
    assert output.request is request
    assert output.request.correction_count == 3
    assert asdict(request) == before
    assert output.request.review is review
    assert output.request.history[0] is history
    assert output.reasons[0].references == ('correction_count',)
    assert disk == {p: p.read_bytes() for p in disk}
    runner.run.assert_not_called()
    c['repository'].save.assert_not_called()
    c['approvals'].save.assert_not_called()


def request_at_count(case, count=2):
    from application.correction_continuation import ContinuationInput, ExistingAssessment, EarlyStopCondition
    _, review, history, _ = case
    history = replace(history, correction_count_before=max(0, count - 1), correction_count=count)
    safety = ExistingAssessment(EarlyStopCondition.SAFE_CONTINUATION, True,
        'Existing Review confirms sufficient history comparison and safe in-scope correction.',
        ('review.report.safe_scope_reason', 'review.report.rationale', 'history.0'))
    return ContinuationInput(review, count, (history,), assessments=(safety,))


def decide(request):
    from application.evaluate_correction_continuation import EvaluateCorrectionContinuationUseCase
    return EvaluateCorrectionContinuationUseCase().execute(request)


@pytest.mark.parametrize('count,expected', [(2, 'CONTINUATION_ALLOWED'), (3, 'STOPPED'), (4, 'STOPPED')])
def test_count_boundary_reads_without_increment_or_reset(continuation_case, count, expected):
    request = request_at_count(continuation_case, count)
    snapshot = asdict(request)
    output = decide(request)
    assert output.decision == expected
    assert asdict(request) == snapshot


@pytest.mark.parametrize('result,expected', [('APPROVED', 'CORRECTION_NOT_NEEDED'),
    ('HUMAN_REVIEW_REQUIRED', 'STOPPED'), (None, 'UNDETERMINED')])
def test_result_contract_precedes_count_and_never_reclassifies(continuation_case, result, expected):
    from application.review_result import ReviewResult
    request = request_at_count(continuation_case, 3)
    value = ReviewResult(result) if result else None
    report = replace(request.review.report, proposed_result=value) if value else None
    review = replace(request.review, result=value, report=report)
    request = replace(request, review=review)
    assert decide(request).decision == expected
    assert request.review.result == value


@pytest.mark.parametrize('field', ['review_failures', 'execution_error', 'parse_error', 'validation_errors'])
def test_unresolved_review_failure_is_undetermined_even_at_limit(continuation_case, field):
    request = request_at_count(continuation_case, 3)
    value = ('failure',) if field.endswith('s') else 'failure'
    request = replace(request, review=replace(request.review, **{field: value}))
    assert decide(request).decision == 'UNDETERMINED'


@pytest.mark.parametrize('count', [None, -1, True, 2.5])
def test_invalid_count_is_not_reconstructed(continuation_case, count):
    request = replace(request_at_count(continuation_case), correction_count=count)
    assert decide(request).decision == 'UNDETERMINED'


@pytest.mark.parametrize('missing', ['history', 'evidence', 'safety', 'scope'])
def test_missing_required_information_cannot_allow_continuation(continuation_case, missing):
    request = request_at_count(continuation_case)
    if missing == 'history':
        request = replace(request, history=())
    elif missing == 'safety':
        request = replace(request, assessments=())
    else:
        prepared = request.review.review.prepared
        evidence = prepared.review_input.evidence
        evidence = None if missing == 'evidence' else replace(evidence, scope=None)
        prepared = replace(prepared, review_input=replace(prepared.review_input, evidence=evidence))
        request = replace(request, review=replace(request.review, review=replace(request.review.review, prepared=prepared)))
    assert decide(request).decision == 'UNDETERMINED'


def with_current_input(request, **changes):
    review = request.review.review
    prepared = replace(review.prepared, review_input=replace(review.prepared.review_input, **changes))
    return replace(request, review=replace(request.review, review=replace(review, prepared=prepared)))


@pytest.mark.parametrize('field,reason', [('out_of_scope_changes', 'SCOPE_VIOLATION'),
                                       ('unplanned_changes', 'PLAN_DEVIATION')])
def test_explicit_evidence_deviation_stops_even_with_safe_assessment(continuation_case, field, reason):
    request = request_at_count(continuation_case)
    evidence = request.review.review.prepared.review_input.evidence
    evidence = replace(evidence, deviations=replace(evidence.deviations, **{field: ('outside.py',)}))
    output = decide(with_current_input(request, evidence=evidence))
    assert output.decision == 'STOPPED'
    assert reason in [r.code for r in output.reasons]


@pytest.mark.parametrize('condition', ['REPEATED_ISSUE', 'PLAN_DEVIATION', 'UNREASONABLE_FILE_GROWTH',
    'TEST_REGRESSION', 'TEST_DETERIORATION', 'NEW_TEST_EXECUTION_ERROR', 'NEW_ERROR_OR_MAJOR_WARNING',
    'UNSOLVABLE_WITHIN_PLAN', 'SPECIFICATION_UNCERTAINTY', 'PLAN_REVISION_REQUIRED',
    'ARCHITECTURE_DECISION_REQUIRED', 'SCOPE_VIOLATION', 'CRITICAL_CHANGE', 'UNSAFE_CAUSE_OR_IMPACT', 'NON_CONVERGENCE'])
def test_explicit_existing_semantic_assessment_is_preserved_without_new_evaluation(continuation_case, condition):
    from application.correction_continuation import ExistingAssessment, EarlyStopCondition
    request = request_at_count(continuation_case)
    # The caller projects an already established finding, not a Target 8 AI decision.
    batch = request.review.review.batch
    finding = replace(batch.aspects[0].findings[0], description=f'Established {condition}',
                      rationale='Established from comparison in the existing Review')
    aspect = replace(batch.aspects[0], findings=(finding,))
    reviewed = replace(request.review.review, batch=replace(batch, aspects=(aspect, *batch.aspects[1:])))
    request = replace(request, review=replace(request.review, review=reviewed))
    assessment = ExistingAssessment(EarlyStopCondition(condition), True, finding.rationale,
                                   ('review.review.batch.aspects.0.findings.0',))
    request = replace(request, assessments=(*request.assessments, assessment))
    before = asdict(request)
    output = decide(request)
    assert output.decision == 'STOPPED'
    assert output.reasons[0].code == condition
    assert output.reasons[0].rationale == finding.rationale
    assert output.reasons[0].references == assessment.references
    assert asdict(request) == before


@pytest.mark.parametrize('condition', ['REPEATED_ISSUE', 'NEW_ERROR_OR_MAJOR_WARNING', 'UNREASONABLE_FILE_GROWTH',
                                      'NON_CONVERGENCE', 'ARCHITECTURE_DECISION_REQUIRED', 'UNSAFE_CAUSE_OR_IMPACT'])
def test_unknown_semantic_assessment_never_falls_back_to_allow(continuation_case, condition):
    from application.correction_continuation import ExistingAssessment, EarlyStopCondition
    request = request_at_count(continuation_case)
    assessment = ExistingAssessment(EarlyStopCondition(condition), None, 'Existing Review cannot settle this question',
                                   ('review.report',))
    request = replace(request, assessments=(*request.assessments, assessment))
    assert decide(request).decision == 'UNDETERMINED'


@pytest.mark.parametrize('status,result,reason', [('COMPLETED', 'FAIL', 'TEST_REGRESSION'),
                                                ('ERROR', 'NONE', 'NEW_TEST_EXECUTION_ERROR')])
@pytest.mark.parametrize('confirmed', [True, None, False])
def test_test_change_requires_explicit_correspondence(continuation_case, status, result, reason, confirmed):
    from application.correction_continuation import TestCorrespondence
    request = request_at_count(continuation_case)
    state = request.review.review.prepared.review_input.test_state
    request = with_current_input(request, test_state=replace(state, target_test_status=status, target_test_result=result))
    correspondence = TestCorrespondence('target', confirmed, 'Existing review identifies the same required test set',
        ('review.review.prepared.review_input.tests', 'history.0.routing.request.review.review.prepared.review_input.tests'))
    request = replace(request, test_correspondences=(correspondence,))
    output = decide(request)
    assert output.decision == ('STOPPED' if confirmed else 'UNDETERMINED')
    if confirmed:
        assert reason in [r.code for r in output.reasons]


def test_unmatched_test_change_is_not_inferred_from_command_text(continuation_case):
    request = request_at_count(continuation_case)
    state = request.review.review.prepared.review_input.test_state
    request = with_current_input(request, test_state=replace(state, target_test_result='FAIL'))
    assert decide(request).decision == 'UNDETERMINED'


def test_initial_expected_failure_is_not_a_regression(continuation_case):
    request = request_at_count(continuation_case)
    assert request.review.review.prepared.review_input.test_state.initial_test_result == 'FAIL'
    assert decide(request).decision == 'CONTINUATION_ALLOWED'


def test_known_cycle_scope_failure_is_preserved_and_stops(continuation_case):
    from application.correction_cycle import CycleFailure
    request = request_at_count(continuation_case)
    request = replace(request, history=(replace(request.history[0], failures=(CycleFailure('scope_violation', 'outside.py'),)),))
    assert decide(request).decision == 'STOPPED'


@pytest.mark.parametrize('mode', ['BATCH', 'STAGED'])
@pytest.mark.parametrize('count,expected', [(2, 'CONTINUATION_ALLOWED'), (3, 'STOPPED')])
def test_preserves_every_artifact_and_retry_without_starting_any_work(continuation_case, monkeypatch, mode, count, expected):
    from unittest.mock import Mock
    from application.review_retry import ReviewRetryHistory, ReviewAIOperation, ReviewOperationKind, AIExecutionAttempt
    from core.ai.ai_request import AIRequest
    from core.ai.ai_response import AIResponse
    from test_classify_review_result import staged
    request = request_at_count(continuation_case, count)
    if mode == 'STAGED':
        request = replace(request, review=replace(request.review, review=staged(request.review.review)))
    operation = ReviewAIOperation(uuid4(), ReviewOperationKind.BATCH, AIRequest('already executed'), request.review.review)
    retry = ReviewRetryHistory(operation, AIExecutionAttempt(execution_error='temporary'),
                               AIExecutionAttempt(AIResponse('recovered', True)))
    request = replace(request, retry_history=(retry,))
    snapshot = asdict(request)
    c = continuation_case[0]
    disk = {p: p.read_bytes() for p in c['request'].repository_path.rglob('*') if p.is_file()}
    forbidden = Mock(side_effect=AssertionError('Target 8 must not execute work'))
    for target in ('application.prepare_correction.PrepareCorrectionUseCase.execute',
                   'application.execute_correction_cycle.ExecuteCorrectionCycleUseCase.execute',
                   'core.ai.ai_service.AIService.run', 'core.ai.codex_runner.CodexRunner.run',
                   'application.collect_implementation_evidence.CollectImplementationEvidenceUseCase.execute',
                   'application.review_with_retry.ReviewWithRetryUseCase.execute',
                   'application.execute_correction_cycle.transition_state', 'subprocess.Popen'):
        monkeypatch.setattr(target, forbidden)
    output = decide(request)
    assert output.decision == expected
    assert request.correction_count == count
    assert output.request.retry_history[0] is retry
    assert asdict(request) == snapshot
    assert disk == {p: p.read_bytes() for p in c['request'].repository_path.rglob('*') if p.is_file()}
    forbidden.assert_not_called()
    c['repository'].save.assert_not_called()
    c['approvals'].save.assert_not_called()


def test_approved_does_not_evaluate_semantic_assessments(continuation_case, monkeypatch):
    from application.review_result import ReviewResult
    from unittest.mock import Mock
    request = request_at_count(continuation_case, 3)
    review = replace(request.review, result=ReviewResult.APPROVED,
                     report=replace(request.review.report, proposed_result=ReviewResult.APPROVED))
    request = replace(request, review=review)
    forbidden = Mock(side_effect=AssertionError('No independent semantic evaluation for APPROVED'))
    monkeypatch.setattr('application.evaluate_correction_continuation._grounded', forbidden)
    assert decide(request).decision == 'CORRECTION_NOT_NEEDED'
    forbidden.assert_not_called()


@pytest.mark.parametrize('reference', ['review.missing', 'history.99', '', 'assessments.0', 'history.-1'])
def test_invalid_provenance_cannot_allow(continuation_case, reference):
    request = request_at_count(continuation_case)
    request = replace(request, assessments=(replace(request.assessments[0], references=(reference,)),))
    assert decide(request).decision == 'UNDETERMINED'


def test_duplicate_conflicting_assessments_cannot_be_normalized_to_safe(continuation_case):
    request = request_at_count(continuation_case)
    safe = request.assessments[0]
    request = replace(request, assessments=(replace(safe, established=False), safe))
    assert decide(request).decision == 'UNDETERMINED'


@pytest.mark.parametrize('missing', ['previous_evidence', 'test_state', 'history_link', 'history_count'])
def test_missing_or_inconsistent_history_cannot_allow(continuation_case, missing):
    request = request_at_count(continuation_case)
    last = request.history[0]
    if missing == 'test_state':
        request = with_current_input(request, test_state=None)
    elif missing == 'history_link':
        request = replace(request, history=(replace(last, previous_evidence_id=uuid4()),))
    elif missing == 'history_count':
        request = replace(request, history=(replace(last, correction_count=1),))
    else:
        previous = last.routing.request.review
        prepared = replace(previous.review.prepared,
                           review_input=replace(previous.review.prepared.review_input, evidence=None))
        previous = replace(previous, review=replace(previous.review, prepared=prepared))
        routing = replace(last.routing, request=replace(last.routing.request, review=previous))
        request = replace(request, history=(replace(last, routing=routing),))
    assert decide(request).decision == 'UNDETERMINED'


def test_existing_review_unconfirmed_information_is_not_silently_ignored(continuation_case):
    request = request_at_count(continuation_case)
    batch = request.review.review.batch
    aspect = replace(batch.aspects[0], unconfirmed=('Cannot determine whether the warning is major',))
    review = replace(request.review.review, batch=replace(batch, aspects=(aspect, *batch.aspects[1:])))
    request = replace(request, review=replace(request.review, review=review))
    assert decide(request).decision == 'UNDETERMINED'


def test_initial_count_zero_uses_initial_evidence_without_inventing_history(continuation_case):
    from application.correction_continuation import ContinuationInput
    _, _, history, _ = continuation_case
    previous = history.routing.request.review
    safety = replace(request_at_count(continuation_case).assessments[0],
                     references=('review.report.safe_scope_reason', 'review.report.rationale'))
    request = ContinuationInput(previous, 0, assessments=(safety,))
    assert decide(request).decision == 'CONTINUATION_ALLOWED'
    assert request.history == ()


def test_human_questions_survive_stop(continuation_case):
    from application.review_result import ReviewResult
    request = request_at_count(continuation_case)
    questions = ('Human must define additional correction permission; do not reset Count.',)
    review = replace(request.review, result=ReviewResult.HUMAN_REVIEW_REQUIRED,
                     report=replace(request.review.report, proposed_result=ReviewResult.HUMAN_REVIEW_REQUIRED,
                                    human_questions=questions))
    output = decide(replace(request, review=review))
    assert output.decision == 'STOPPED'
    assert output.request.review.report.human_questions is questions


def test_raw_warning_growth_and_matching_finding_text_do_not_invent_stop_rules(continuation_case):
    request = request_at_count(continuation_case)
    inp = request.review.review.prepared.review_input
    request = with_current_input(request, test_state=replace(inp.test_state, warnings=('unclassified warning',)))
    # No existing judgment of significance or sufficiency was supplied.
    request = replace(request, assessments=())
    assert decide(request).decision == 'UNDETERMINED'


def test_unavailable_test_evidence_prevents_safe_fallback(continuation_case):
    request = request_at_count(continuation_case)
    state = request.review.review.prepared.review_input.test_state
    request = with_current_input(request, test_state=replace(state, unavailable_evidence=('Required test record unavailable',)))
    assert decide(request).decision == 'UNDETERMINED'


def test_initial_evidence_cannot_silently_reset_recorded_chain_count(continuation_case):
    request = request_at_count(continuation_case)
    previous = request.history[0].routing.request.review
    request = replace(request, review=previous, correction_count=0)
    assert decide(request).decision == 'UNDETERMINED'


def test_unrelated_history_entries_cannot_supply_chain_comparison(continuation_case):
    request = request_at_count(continuation_case)
    unrelated = replace(request.history[0], new_evidence_id=uuid4(), correction_count=1)
    request = replace(request, history=(unrelated, request.history[0]))
    assert decide(request).decision == 'UNDETERMINED'


@pytest.mark.parametrize('phase', ['target', 'full'])
def test_persistent_fail_is_not_new_regression_or_technical_error(continuation_case, phase):
    request = request_at_count(continuation_case)
    state = request.review.review.prepared.review_input.test_state
    failed = replace(state, **{f'{phase}_test_result': 'FAIL'})
    request = with_current_input(request, test_state=failed)
    last = request.history[0]
    old = last.routing.request.review
    old_prepared = replace(old.review.prepared, review_input=replace(old.review.prepared.review_input, test_state=failed))
    old = replace(old, review=replace(old.review, prepared=old_prepared))
    last = replace(last, routing=replace(last.routing, request=replace(last.routing.request, review=old)))
    request = replace(request, history=(last,))
    assert decide(request).decision == 'CONTINUATION_ALLOWED'


def test_staged_unconfirmed_assessment_is_preserved(continuation_case):
    from test_classify_review_result import staged
    request = request_at_count(continuation_case)
    review = staged(request.review.review)
    integration = replace(review.integration, assessment=replace(review.integration.assessment, unconfirmed=('Unknown convergence',)))
    request = replace(request, review=replace(request.review, review=replace(review, integration=integration)))
    assert decide(request).decision == 'UNDETERMINED'


def test_missing_underlying_stage_is_review_failure_even_with_a_result(continuation_case):
    from test_classify_review_result import staged
    request = request_at_count(continuation_case)
    review = replace(staged(request.review.review), integration=None)
    request = replace(request, review=replace(request.review, review=review))
    assert decide(request).decision == 'UNDETERMINED'


def test_previous_safety_alone_cannot_authorize_current_correction(continuation_case):
    request = request_at_count(continuation_case)
    assessment = replace(request.assessments[0], references=('history.0.routing.request.review.report.safe_scope_reason',))
    assert decide(replace(request, assessments=(assessment,))).decision == 'UNDETERMINED'


def test_missing_initial_actual_test_state_cannot_be_declared_sufficient(continuation_case):
    from application.correction_continuation import ContinuationInput
    previous = continuation_case[2].routing.request.review
    safety = replace(request_at_count(continuation_case).assessments[0], references=('review.report.safe_scope_reason',))
    request = ContinuationInput(previous, 0, assessments=(safety,))
    assert decide(with_current_input(request, test_state=None)).decision == 'UNDETERMINED'
