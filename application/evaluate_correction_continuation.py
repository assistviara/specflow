from application.correction_continuation import (
    ContinuationDecision as Decision, ContinuationOutput, ContinuationReason,
    EarlyStopCondition, ContinuationInput,
)
from application.classify_review_result import _review_failures
from application.review_result import ReviewResult


def _resolve(request, reference):
    value = request
    for part in reference.split('.'):
        if isinstance(value, (tuple, list)):
            if not part.isdecimal():
                raise ValueError('Reference index must be nonnegative')
            value = value[int(part)]
        elif isinstance(value, dict):
            value = value[part]
        else:
            if part.startswith('_'):
                raise ValueError('Reference must identify artifact content')
            value = getattr(value, part)
    return value


def _grounded(request, assessment):
    if not assessment.rationale.strip() or not assessment.references:
        return False
    try:
        return all(ref.startswith(('review.', 'history.')) and bool(_resolve(request, ref))
                   for ref in assessment.references)
    except (AttributeError, KeyError, IndexError, ValueError, TypeError):
        return False


def _test_changes(request, current, previous):
    stopped, unknown = [], []
    if current is None or previous is None or current.unavailable_evidence or previous.unavailable_evidence:
        return stopped, [ContinuationReason('TEST_COMPARISON_UNAVAILABLE',
            'Previous and current acquired Test State are required.', ('review.review.prepared', 'history'))]
    confirmations = {}
    for item in request.test_correspondences:
        if item.phase not in ('target', 'full') or item.phase in confirmations or not _grounded(request, item):
            unknown.append(ContinuationReason('TEST_CORRESPONDENCE_INVALID',
                'A unique, grounded target/full correspondence is required.', item.references))
        else:
            confirmations[item.phase] = item
    for phase in ('target', 'full'):
        old_status, new_status = (getattr(state, f'{phase}_test_status') for state in (previous, current))
        old_result, new_result = (getattr(state, f'{phase}_test_result') for state in (previous, current))
        code = None
        if old_status == 'COMPLETED' and new_status == 'ERROR':
            code = 'NEW_TEST_EXECUTION_ERROR'
        elif old_status == new_status == 'COMPLETED' and old_result == 'PASS' and new_result == 'FAIL':
            code = 'TEST_REGRESSION'
        confirmation = confirmations.get(phase)
        if code or (confirmation is not None and confirmation.confirmed is not True):
            refs = (f'history.{len(request.history) - 1}.routing.request.review.review.prepared.review_input.test_state',
                    'review.review.prepared.review_input.test_state')
            if confirmation is None or confirmation.confirmed is not True:
                unknown.append(ContinuationReason('TEST_CORRESPONDENCE_UNCONFIRMED',
                    f'{phase} test correspondence has not been established; no regression is inferred.', refs))
            elif code:
                stopped.append(ContinuationReason(code, confirmation.rationale, (*refs, *confirmation.references)))
    return stopped, unknown


def _unconfirmed(review):
    if review.mode == 'BATCH' and review.batch:
        return tuple(f'review.review.batch.aspects.{i}.unconfirmed'
                     for i, aspect in enumerate(review.batch.aspects) if aspect.unconfirmed)
    references = [f'review.review.stages.{i}.assessment.unconfirmed'
                  for i, stage in enumerate(review.stages) if stage.assessment and stage.assessment.unconfirmed]
    if review.integration and review.integration.assessment and review.integration.assessment.unconfirmed:
        references.append('review.review.integration.assessment.unconfirmed')
    return tuple(references)


class EvaluateCorrectionContinuationUseCase:
    def execute(self, request: ContinuationInput) -> ContinuationOutput:
        def output(decision, code, rationale, *references):
            return ContinuationOutput(request, decision, (ContinuationReason(code, rationale, references),))

        review = request.review
        if (review.result is None or review.review_failures or review.execution_error or review.parse_error
                or review.validation_errors or _review_failures(review.review)
                or any(h.recovery_failed for h in request.retry_history)):
            return output(Decision.UNDETERMINED, 'REVIEW_NOT_ESTABLISHED',
                          'A required Review result is unavailable or has unresolved failure.', 'review', 'retry_history')
        if review.report is None or review.report.proposed_result != review.result:
            return output(Decision.UNDETERMINED, 'REVIEW_REPORT_UNAVAILABLE',
                          'The established Review report is required.', 'review')
        if review.result == ReviewResult.APPROVED:
            return output(Decision.CORRECTION_NOT_NEEDED, 'APPROVED',
                          'The established Review requires no next correction.', 'review.result')
        if review.result == ReviewResult.HUMAN_REVIEW_REQUIRED:
            return output(Decision.STOPPED, 'HUMAN_REVIEW_REQUIRED',
                          'The existing Review requires Human judgment.', 'review.report')
        if review.result != ReviewResult.REVISION_REQUIRED:
            return output(Decision.UNDETERMINED, 'REVIEW_NOT_ESTABLISHED', 'Unknown Result.', 'review.result')
        count = request.correction_count
        if type(count) is not int or count < 0:
            return output(Decision.UNDETERMINED, 'COUNT_UNAVAILABLE',
                          'A nonnegative recorded Correction Count is required.', 'correction_count')
        if count >= 3:
            return ContinuationOutput(request, Decision.STOPPED, (
                ContinuationReason('MAX_CORRECTION_COUNT_REACHED',
                                   'The normal maximum of three corrections has been reached. Further permission requires Human judgment; no reset is inferred.',
                                   ('correction_count',)),
            ))
        inp = review.review.prepared.review_input
        if inp.evidence is None or inp.evidence.scope is None:
            return output(Decision.UNDETERMINED, 'EVIDENCE_UNAVAILABLE',
                          'Current Evidence and approved Scope are required.', 'review.review.prepared')
        if request.history or count or inp.evidence.identity.previous_evidence_id is not None:
            if not request.history:
                return output(Decision.UNDETERMINED, 'HISTORY_UNAVAILABLE',
                              'Correction history is required for this continuation.', 'history')
            last = request.history[-1]
            if (last.correction_count != count or last.new_evidence_id != inp.evidence.identity.evidence_id
                    or last.implementation_id != inp.evidence.identity.implementation_id
                    or last.previous_evidence_id != inp.evidence.identity.previous_evidence_id):
                return output(Decision.UNDETERMINED, 'HISTORY_MISMATCH',
                              'History, recorded Count and current Evidence do not correspond.', 'history', 'correction_count')
            previous = last.routing.request.review.review.prepared.review_input
            if previous is None or previous.evidence is None or previous.evidence.identity.evidence_id != last.previous_evidence_id:
                return output(Decision.UNDETERMINED, 'PREVIOUS_EVIDENCE_UNAVAILABLE',
                              'The preceding Evidence must remain traceable.', 'history')
            for before, after in zip(request.history, request.history[1:]):
                if (before.new_evidence_id is None or before.new_evidence_id != after.previous_evidence_id
                        or before.correction_count != after.correction_count_before):
                    return output(Decision.UNDETERMINED, 'HISTORY_CHAIN_MISMATCH',
                                  'Supplied histories do not form a corresponding Correction Chain.', 'history')

        reasons = []
        unknown = []
        if inp.test_state is None or inp.test_state.unavailable_evidence:
            unknown.append(ContinuationReason('TEST_STATE_UNAVAILABLE',
                'The current acquired Test State is incomplete.', ('review.review.prepared.review_input.test_state',)))
        unconfirmed = _unconfirmed(review.review)
        if unconfirmed:
            unknown.append(ContinuationReason('REVIEW_INFORMATION_UNCONFIRMED',
                'Existing Review retains unconfirmed information needed for safe continuation.', unconfirmed))
        for field, code in (('out_of_scope_changes', 'SCOPE_VIOLATION'), ('unplanned_changes', 'PLAN_DEVIATION')):
            if getattr(inp.evidence.deviations, field):
                reasons.append(ContinuationReason(code, 'Current Evidence explicitly records a deviation.',
                    (f'review.review.prepared.review_input.evidence.deviations.{field}',)))
        if request.history:
            last = request.history[-1]
            for index, failure in enumerate(last.failures):
                if failure.kind == 'scope_violation':
                    reasons.append(ContinuationReason('SCOPE_VIOLATION', failure.detail,
                        (f'history.{len(request.history) - 1}.failures.{index}',)))
            previous = last.routing.request.review.review.prepared.review_input
            test_stops, test_unknown = _test_changes(request, inp.test_state,
                                                   previous.test_state if previous else None)
            reasons.extend(test_stops)
            unknown.extend(test_unknown)
        safe = False
        for assessment in request.assessments:
            if (not isinstance(assessment.condition, EarlyStopCondition)
                    or type(assessment.established) not in (bool, type(None)) or not _grounded(request, assessment)):
                unknown.append(ContinuationReason('ASSESSMENT_UNGROUNDED',
                    'An existing assessment and resolvable evidence references are required.', assessment.references))
                continue
            reason = ContinuationReason(assessment.condition.value, assessment.rationale, assessment.references)
            if assessment.condition == EarlyStopCondition.SAFE_CONTINUATION:
                safe = assessment.established is True and any(ref.startswith('review.') for ref in assessment.references)
                if not safe:
                    unknown.append(reason)
            elif assessment.established is True:
                reasons.append(reason)
            elif assessment.established is None:
                unknown.append(reason)
        if reasons:
            return ContinuationOutput(request, Decision.STOPPED, tuple(reasons))
        if unknown:
            return ContinuationOutput(request, Decision.UNDETERMINED, tuple(unknown))
        if not safe or not review.report.safe_scope_reason.strip() or review.report.human_questions:
            return output(Decision.UNDETERMINED, 'SAFE_CONTINUATION_UNCONFIRMED',
                          'Existing artifacts must explicitly establish sufficient comparison and safe in-scope correction.',
                          'review.report', 'history')
        return output(Decision.CONTINUATION_ALLOWED, 'SAFE_CONTINUATION_CONFIRMED',
                      'The recorded Count is below three and existing assessments confirm safe continuation.',
                      'review.report', 'history', 'assessments')
