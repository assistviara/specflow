from application.review_handoff import HandoffType, ReviewHandoffOutput, HandoffDiagnostic, ReviewHandoffInput
from application.review_result import ReviewResult
from application.evaluate_correction_continuation import _resolve
from application.correction_continuation import ContinuationDecision
from application.classify_review_result import _review_failures


ROOT = 'continuation.request.review'
INPUT = ROOT + '.review.prepared.review_input'
# Existing Specification section 10.1 values; this is not a transition policy.
STATES = frozenset(('specification_ready', 'plan_generating', 'plan_approval_pending',
    'plan_revision_requested', 'plan_approved', 'implementation_prompt_generating',
    'implementation_ready', 'implementing', 'critical_approval_pending', 'implementation_failed',
    'implementation_completed', 'reviewing', 'review_failed', 'final_approval_pending',
    'correction_requested', 'completed', 'cancelled'))


def _critical_refs(request):
    change = request.critical_change
    return (() if change is None else (change.content_reference, change.reason_reference,
                                      change.targets_reference, change.impact_reference))


def _cycle_issues(request):
    refs = list(request.unresolved_references)
    history = request.continuation.request.history
    if history:
        refs.extend(f'continuation.request.history.{len(history) - 1}.failures.{i}'
                    for i in range(len(history[-1].failures)))
    if request.cycle:
        refs.extend(f'cycle.failures.{i}' for i in range(len(request.cycle.failures)))
    return tuple(refs)


def _validate(request):
    errors = []
    def error(code, detail, *refs):
        errors.append(HandoffDiagnostic(code, detail, refs))
    continuation = request.continuation
    if continuation is None or continuation.request is None:
        error('INPUT_MISSING', 'ContinuationOutput is required.', 'continuation')
        return tuple(errors)
    review = continuation.request.review
    if review is None or review.review is None or review.review.prepared is None or review.review.prepared.acquired is None:
        error('INPUT_MISSING', 'The upstream Review output is required.', ROOT)
        return tuple(errors)
    acquired = review.review.prepared.acquired
    if review.result is not None and review.result not in tuple(ReviewResult):
        error('REVIEW_RESULT_INVALID', 'Unknown upstream Review Result.', ROOT + '.result')
    if review.result is not None and review.report is None:
        error('REVIEW_REPORT_MISSING', 'An established Result requires its existing Review Report.', ROOT + '.report')
    if review.result is not None and review.report and review.report.proposed_result != review.result:
        error('REVIEW_REPORT_MISMATCH', 'Established Result and Review Report do not correspond.', ROOT)
    if request.implementation_id is None or request.implementation_id != acquired.request.implementation_id:
        error('IDENTITY_MISMATCH', 'Handoff identity does not match the acquired implementation.',
              'implementation_id', ROOT + '.review.prepared.acquired.request')
    inp = review.review.prepared.review_input
    if inp and inp.request.implementation_id != request.implementation_id:
        error('INPUT_IDENTITY_MISMATCH', 'Review Input does not identify the handoff implementation.', INPUT + '.request')
    if inp and inp.evidence and inp.evidence.identity.implementation_id != request.implementation_id:
        error('IDENTITY_MISMATCH', 'Current Evidence does not identify the handoff implementation.', INPUT + '.evidence.identity')
    if inp and inp.evidence and inp.evidence.identity.evidence_id != inp.request.evidence_id:
        error('EVIDENCE_REFERENCE_MISMATCH', 'Current Evidence differs from the Review Input reference.', INPUT + '.evidence.identity')
    if not request.current_state:
        error('STATE_MISSING', 'The current State is required.', 'current_state')
    elif review.result == ReviewResult.HUMAN_REVIEW_REQUIRED and request.current_state != 'reviewing':
        error('STATE_MISMATCH', 'HUMAN_REVIEW_REQUIRED must retain reviewing.', 'current_state')
    elif request.current_state not in STATES:
        error('STATE_UNKNOWN', 'State is not one of the existing Specification states.', 'current_state')
    if continuation.decision not in tuple(ContinuationDecision):
        error('CONTINUATION_INVALID', 'Unknown Continuation Decision.', 'continuation.decision')
    if not continuation.reasons or any(not r.code.strip() or not r.rationale.strip() for r in continuation.reasons):
        error('CONTINUATION_REASON_MISSING', 'Existing continuation reasons must remain traceable.', 'continuation.reasons')
    required = (*request.required_references, *request.unresolved_references, *_critical_refs(request))
    for ref in required:
        try:
            if not ref.startswith(('continuation.', 'cycle.')):
                raise ValueError('Reference must identify acquired upstream content')
            value = _resolve(request, ref)
            if value is None or callable(value):
                raise ValueError('Required artifact is unavailable')
            if ref in _critical_refs(request) and not value:
                raise ValueError('Critical Change content, reason, targets and impact must be established')
        except (AttributeError, KeyError, IndexError, ValueError, TypeError) as exc:
            error('REFERENCE_UNAVAILABLE', str(exc), ref)
    for reason in continuation.reasons:
        for ref in reason.references:
            try:
                # A valid path to None/empty is meaningful upstream missing-information evidence.
                _resolve(continuation.request, ref)
            except (AttributeError, KeyError, IndexError, ValueError, TypeError) as exc:
                error('TRIGGER_REFERENCE_INVALID', str(exc), 'continuation.request.' + ref)
    if any(r.code == 'CRITICAL_CHANGE' for r in continuation.reasons) and request.critical_change is None:
        error('CRITICAL_INFORMATION_MISSING', 'Explicit Critical Change requires traceable change information.', 'continuation.reasons')
    candidates = _cycle_issues(request)
    seen = set()
    for resolution in request.resolutions:
        try:
            if (resolution.issue_reference not in candidates or resolution.issue_reference in seen
                    or not resolution.resolution_reference.startswith(ROOT + '.report.')
                    or not _resolve(request, resolution.issue_reference)
                    or not _resolve(request, resolution.resolution_reference)):
                raise ValueError('Resolution must link a retained issue to explicit current Review report content')
            seen.add(resolution.issue_reference)
        except (AttributeError, KeyError, IndexError, ValueError, TypeError) as exc:
            error('RESOLUTION_REFERENCE_INVALID', str(exc), resolution.issue_reference, resolution.resolution_reference)
    if request.cycle:
        cycle = request.cycle
        if cycle.history and cycle.history.implementation_id != request.implementation_id:
            error('CYCLE_IDENTITY_MISMATCH', 'Cycle does not identify the handoff implementation.', 'cycle.history')
        if cycle.re_review and cycle.re_review.classification != review:
            error('CYCLE_REVIEW_MISMATCH', 'Current Review differs from the supplied Cycle Re-Review.', 'cycle.re_review', ROOT)
        if cycle.current_state != request.current_state:
            error('CYCLE_STATE_MISMATCH', 'Current State differs from supplied Cycle State.', 'cycle.current_state')
    return tuple(errors)


def _phase_six_input_failure(request):
    review = request.continuation.request.review
    inp = review.review.prepared.review_input
    if inp is None or inp.evidence is None or inp.repository_state is None or review.report is None:
        return HandoffDiagnostic('PHASE_6_INPUT_MISSING',
            'Current Evidence, Review report and acquired Repository information are required.', (INPUT,))
    if inp.evidence.identity.implementation_kind == 'CORRECTION':
        history = request.continuation.request.history
        if not history:
            return HandoffDiagnostic('CORRECTION_HISTORY_MISSING',
                'Current Correction Evidence requires its existing History reference.', ('continuation.request.history',))
        last = history[-1]
        if (last.new_evidence_id != inp.evidence.identity.evidence_id
                or last.implementation_id != request.implementation_id
                or last.previous_evidence_id != inp.evidence.identity.previous_evidence_id):
            return HandoffDiagnostic('CORRECTION_HISTORY_MISMATCH',
                'Current Correction Evidence and supplied History do not correspond.', ('continuation.request.history', INPUT))
    return None


def _references(request):
    refs = [ROOT, 'continuation', 'continuation.request.history', 'continuation.request.retry_history', 'current_state', 'implementation_id']
    prepared = request.continuation.request.review.review.prepared
    refs.append(ROOT + '.review.prepared')
    if prepared.review_input is not None:
        for field in ('evidence', 'sources', 'saved_diff', 'repository_state', 'test_state', 'approval_records'):
            if getattr(prepared.review_input, field) is not None:
                refs.append(INPUT + '.' + field)
    if request.cycle:
        refs.append('cycle')
    return tuple((*refs, *request.required_references, *_critical_refs(request), *request.unresolved_references,
                  *(r.resolution_reference for r in request.resolutions)))


class PrepareReviewHandoffUseCase:
    def execute(self, request: ReviewHandoffInput) -> ReviewHandoffOutput:
        failures = _validate(request)
        if failures:
            return ReviewHandoffOutput(request, HandoffType.NONE, ('TARGET_9_INPUT_FAILURE',), failures=failures)
        review = request.continuation.request.review
        continuation = request.continuation
        questions = review.report.human_questions if review.report else ()
        reasons = tuple(r.code for r in continuation.reasons)
        upstream_failures = tuple(filter(None, (*review.review_failures, review.execution_error, review.parse_error,
                                  *review.validation_errors, *_review_failures(review.review))))
        upstream_failures += tuple(f'continuation.request.retry_history.{i}'
                                  for i, retry in enumerate(continuation.request.retry_history) if retry.recovery_failed)
        unresolved = (*upstream_failures, *questions, *(review.report.unresolved if review.report else ()))
        resolved = {r.issue_reference for r in request.resolutions}
        unresolved = (*unresolved, *(ref for ref in _cycle_issues(request) if ref not in resolved))
        refs = _references(request)
        if request.critical_change:
            return ReviewHandoffOutput(request, HandoffType.CRITICAL_CHANGE_APPROVAL,
                (*reasons, 'CRITICAL_CHANGE'), questions or (str(_resolve(request, request.critical_change.reason_reference)),),
                (*unresolved, *_critical_refs(request)), refs)
        if continuation.decision in (ContinuationDecision.STOPPED, ContinuationDecision.UNDETERMINED):
            unresolved = (*unresolved, *(r.rationale for r in continuation.reasons))
        if review.result == ReviewResult.APPROVED and continuation.decision == ContinuationDecision.CORRECTION_NOT_NEEDED and not unresolved:
            failure = _phase_six_input_failure(request)
            if failure:
                return ReviewHandoffOutput(request, HandoffType.NONE, ('TARGET_9_INPUT_FAILURE',),
                                          artifact_references=refs, failures=(failure,))
            return ReviewHandoffOutput(request, HandoffType.PHASE_6, ('PHASE_5_READY',), artifact_references=refs)
        if (review.result == ReviewResult.REVISION_REQUIRED
                and continuation.decision == ContinuationDecision.CONTINUATION_ALLOWED and not unresolved):
            return ReviewHandoffOutput(request, HandoffType.NONE, ('NEXT_CORRECTION_CANDIDATE',), artifact_references=refs)
        actions = questions or tuple(unresolved) or tuple(r.rationale for r in continuation.reasons)
        if not actions:
            actions = ('The existing information does not establish a safe handoff; Human judgment is required.',)
        return ReviewHandoffOutput(request, HandoffType.HUMAN_REVIEW,
                                   reasons or ('UPSTREAM_UNRESOLVED',), actions, unresolved or actions, refs)
