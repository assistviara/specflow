from dataclasses import asdict, dataclass, replace
from datetime import datetime
import json
from pathlib import Path
from uuid import uuid4

from application.current_state_repository import load_current_state
from application.state_transition import transition_state
from application.evidence_workflow import EvidenceWorkflowOutput
from application.prepare_review_input import PrepareReviewInputUseCase
from application.review_with_retry import ReviewRetryOutput
from application.correction_continuation import (
    ContinuationInput, ContinuationOutput, ContinuationDecision, ExistingAssessment, TestCorrespondence,
)
from application.correction_cycle import CorrectionCycleInput, CorrectionCycleOutput, ReTestPlan
from application.correction_routing import CorrectionProblem, CorrectionRoutingInput, CorrectionRoutingOutput, RoutingControl
from application.review_result import ReviewResultOutput, ReviewResult
from application.evaluate_correction_continuation import EvaluateCorrectionContinuationUseCase
from application.prepare_review_handoff import PrepareReviewHandoffUseCase
from application.review_handoff import (
    ReviewHandoffInput, ReviewHandoffOutput, HandoffType, CriticalChangeReferences, ExistingIssueResolution,
)


@dataclass(frozen=True)
class ReviewWorkflowInput:
    upstream: EvidenceWorkflowOutput
    mode: str
    artifact_dir: Path


@dataclass(frozen=True)
class CorrectionStepInput:
    # Bind explicit caller facts to the current Review; never reuse prior safety
    # assessments for a newly generated Evidence / Re-Review.
    review: ReviewResultOutput
    assessments: tuple[ExistingAssessment, ...] = ()
    problems: tuple[CorrectionProblem, ...] = ()
    tests: ReTestPlan | None = None
    test_correspondences: tuple[TestCorrespondence, ...] = ()
    critical_change: CriticalChangeReferences | None = None
    resolutions: tuple[ExistingIssueResolution, ...] = ()


@dataclass(frozen=True)
class ReviewWorkflowOutput:
    request: ReviewWorkflowInput
    success: bool = False
    review: ReviewRetryOutput | None = None
    continuation: ContinuationOutput | None = None
    handoff: ReviewHandoffOutput | None = None
    routing: CorrectionRoutingOutput | None = None
    cycles: tuple[CorrectionCycleOutput, ...] = ()
    correction_count: int = 0
    current_state: dict | None = None
    transition: dict | None = None
    artifact_paths: tuple[Path, ...] = ()
    stop_reason: str | None = None

    @property
    def ready_for_final_approval(self):
        return self.success and self.handoff is not None and self.handoff.handoff_type == HandoffType.PHASE_6

    @property
    def waiting_for_human(self):
        return self.success and self.handoff is not None and self.handoff.human_judgment_required


class ReviewWorkflowUseCase:
    """Connect existing Review contracts; never execute Final Approval."""

    def __init__(self, approvals, evidence_repository, repository_state_provider_factory,
                 test_state_provider_factory, reviewer, correction_preparer=None, correction_cycle=None):
        self._approvals = approvals
        self._evidence = evidence_repository
        self._repositories = repository_state_provider_factory
        self._tests = test_state_provider_factory
        self._reviewer = reviewer
        self._correction_preparer = correction_preparer
        self._correction_cycle = correction_cycle

    @staticmethod
    def _entry(request):
        return request.upstream.request.upstream.request.upstream.entry.request

    def _acquire(self, prepared):
        return PrepareReviewInputUseCase(
            evidence_repository=self._evidence, approval_repository=self._approvals,
            repository_state_provider=self._repositories(prepared.acquired.request.repository_path),
            test_state_provider_factory=lambda path, identity: self._tests(
                record_path=path, expected_implementation_id=identity),
        ).execute(prepared.acquired.request)

    def _guard(self, request):
        upstream = request.upstream
        if request.mode not in ('BATCH', 'STAGED'):
            raise ValueError('Explicit BATCH or STAGED mode is required.')
        if (not upstream.success or upstream.stop_reason or upstream.handoff is None
                or upstream.collection is None or not upstream.collection.success
                or upstream.collection.evidence_path is None):
            raise ValueError('Successful Target 4 with saved Evidence is required.')
        prepared = upstream.handoff
        if (prepared.review_input is None or prepared.missing_information
                or prepared.acquisition_errors or prepared.mismatches):
            raise ValueError('Complete Target 4 Review Input is required.')
        evidence = prepared.review_input.evidence
        if (evidence is None or evidence != upstream.collection.implementation_evidence
                or evidence.identity.evidence_id != upstream.collection.evidence_id
                or evidence.identity.implementation_id != upstream.collection.implementation_id
                or evidence.identity.implementation_id != upstream.request.upstream.request.implementation_id
                or evidence.identity.implementation_kind != 'INITIAL'
                or evidence.identity.previous_evidence_id is not None):
            raise ValueError('Initial Implementation / Evidence identity mismatch.')
        acquired = self._acquire(prepared)
        if (acquired.review_input is None or acquired.acquisition_errors or acquired.missing_information
                or acquired.mismatches or acquired.acquired != prepared.acquired
                or prepared.review_input != prepared.acquired):
            raise ValueError('Review artifacts changed or are unavailable since Target 4.')
        state = load_current_state(self._entry(request).state_file)
        if state != upstream.current_state or state.get('status') != 'implementation_completed':
            raise ValueError('Current State must match Target 4 implementation_completed.')
        return prepared, state

    def _finish(self, output):
        try:
            observed = load_current_state(self._entry(output.request).state_file)
            if output.success and observed != output.current_state:
                output = replace(output, success=False, stop_reason='State changed during Review / Handoff.')
            output = replace(output, current_state=observed)
        except Exception as exc:
            output = replace(output, success=False, current_state=None,
                             stop_reason=f'{output.stop_reason or ""} State observation failed: {exc}')
        # A create-only snapshot retains Review, retry diagnostics and Handoff separately
        # from Human Approval and State. Failed writes remain visible, without rollback.
        path = output.request.artifact_dir / f'review_workflow_{uuid4()}.json'
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('x', encoding='utf-8', newline='\n') as stream:
                json.dump(asdict(output), stream, default=str, ensure_ascii=False, indent=2)
            output = replace(output, artifact_paths=(*output.artifact_paths, path))
        except Exception as exc:
            output = replace(output, success=False, stop_reason=f'{output.stop_reason or ""} Review persistence failed: {exc}',
                             artifact_paths=(*output.artifact_paths, path) if path.exists() else output.artifact_paths)
        return output

    def _route(self, output, step=None):
        review = output.review.classification
        history = tuple(cycle.history for cycle in output.cycles if cycle.history is not None)
        continuation = EvaluateCorrectionContinuationUseCase().execute(
            ContinuationInput(review, output.correction_count, history,
                assessments=step.assessments if step else (), retry_history=output.review.history,
                test_correspondences=step.test_correspondences if step else ()))
        identity = review.review.prepared.acquired.request.implementation_id
        handoff = PrepareReviewHandoffUseCase().execute(ReviewHandoffInput(
            continuation, identity, output.current_state['status'],
            cycle=output.cycles[-1] if output.cycles else None,
            critical_change=step.critical_change if step else None,
            resolutions=step.resolutions if step else ()))
        established = (review.result is not None and not review.review_failures and not review.execution_error
                       and not review.parse_error and not review.validation_errors and not output.review.recovery_failed)
        return replace(output, continuation=continuation, handoff=handoff,
                       success=established and not handoff.failures,
                       stop_reason=None if established and not handoff.failures else 'Review / Handoff did not establish a valid result.')

    def start(self, request: ReviewWorkflowInput) -> ReviewWorkflowOutput:
        output = ReviewWorkflowOutput(request)
        try:
            prepared, state = self._guard(request)
            transition = dict(transition_id=str(uuid4()), from_state='implementation_completed', to_state='reviewing',
                              occurred_at=datetime.now().astimezone().isoformat(), reason='Target 5 Review started')
            output = replace(output, current_state=state, transition=transition)
            entry = self._entry(request)
            transition_state(entry.state_file, entry.history_dir, transition)
            state = load_current_state(entry.state_file)
            if state.get('status') != 'reviewing':
                raise ValueError('Review start State was not persisted.')
            output = replace(output, current_state=state)
            reviewed = self._reviewer.execute(prepared, mode=request.mode)
            output = replace(output, review=reviewed)
            output = replace(output, review=self._reviewer.classify(reviewed))
            result = output.review.classification
            if (result.result is None or result.review_failures or result.execution_error
                    or result.parse_error or result.validation_errors or output.review.recovery_failed):
                if load_current_state(entry.state_file) != state:
                    raise ValueError('State changed during failed Review.')
                transition = dict(transition_id=str(uuid4()), from_state='reviewing', to_state='review_failed',
                    occurred_at=datetime.now().astimezone().isoformat(), reason='Review result was not established')
                output = replace(output, transition=transition)
                transition_state(entry.state_file, entry.history_dir, transition)
                output = replace(output, current_state=load_current_state(entry.state_file))
            return self._finish(self._route(output))
        except Exception as exc:
            return self._finish(replace(output, success=False, stop_reason=f'{type(exc).__name__}: {exc}'))

    def correct(self, previous: ReviewWorkflowOutput, step: CorrectionStepInput) -> ReviewWorkflowOutput:
        output = replace(previous, success=False, stop_reason=None, transition=None)
        try:
            if (not previous.success or previous.stop_reason or previous.review is None
                    or previous.review.classification != step.review):
                raise ValueError('Explicit Correction inputs must identify the current successful Review output.')
            entry = self._entry(previous.request)
            state = load_current_state(entry.state_file)
            if state != previous.current_state or state.get('status') != 'reviewing':
                raise ValueError('Current reviewing State is required.')
            if previous.cycles:
                if (any(c.failures or c.history is None or c.history_path is None or not c.history_path.is_file()
                        for c in previous.cycles)
                        or previous.cycles[-1].history.correction_count != previous.correction_count):
                    raise ValueError('Established Correction History / Count is required.')
            elif previous.correction_count != 0:
                raise ValueError('Initial Review cannot supply a fabricated Correction Count.')
            prepared = previous.review.review.prepared
            acquired = self._acquire(prepared)
            if (acquired.review_input is None or acquired.acquisition_errors or acquired.missing_information
                    or acquired.acquired != prepared.acquired or acquired.mismatches != prepared.mismatches):
                raise ValueError('Reviewed artifacts changed before Correction.')
            output = self._route(output, step)
            if (step.review.result != ReviewResult.REVISION_REQUIRED
                    or output.continuation.decision != ContinuationDecision.CONTINUATION_ALLOWED
                    or output.handoff.handoff_type != HandoffType.NONE or output.handoff.failures):
                return self._finish(output)
            if step.tests is None or not step.problems:
                raise ValueError('Explicit Correction Problems and ReTestPlan are required; no Correction was started.')
            if self._correction_preparer is None or self._correction_cycle is None:
                raise ValueError('Existing Correction components are required.')
            routing = self._correction_preparer.execute(CorrectionRoutingInput(
                step.review, step.problems, state['status'], RoutingControl(True, output.correction_count, False, True),
                retry_history=output.review.history))
            output = replace(output, routing=routing)
            if not routing.ready:
                raise ValueError('Correction Routing is not ready.')
            if any(instruction.destination != 'Codex再実装工程' for instruction in routing.instructions):
                raise ValueError('Routing destination is not executable by the existing Correction Cycle.')
            # ReTestPlan validation is the existing Cycle's responsibility. Run it
            # before changing State, using the State required by that component.
            from application.correction_cycle_validation import validate_cycle
            cycle_request = CorrectionCycleInput(routing, entry.state_file, entry.history_dir,
                previous.request.artifact_dir / 'cycles', step.tests)
            failures = validate_cycle(cycle_request, 'correction_requested', self._evidence, self._approvals)
            if failures:
                raise ValueError(f'Correction start conditions failed: {failures}')
            transition = dict(transition_id=str(uuid4()), from_state='reviewing', to_state='correction_requested',
                occurred_at=datetime.now().astimezone().isoformat(), reason='Explicit in-scope Correction authorized by existing Review contracts')
            output = replace(output, success=False, transition=transition)
            transition_state(entry.state_file, entry.history_dir, transition)
            if load_current_state(entry.state_file).get('status') != 'correction_requested':
                raise ValueError('Correction start State was not persisted.')
            cycle = self._correction_cycle.execute(cycle_request)
            output = replace(output, cycles=(*output.cycles, cycle),
                current_state=load_current_state(entry.state_file),
                correction_count=cycle.history.correction_count if cycle.history else output.correction_count)
            if cycle.failures or cycle.re_review is None or cycle.re_review.classification is None:
                raise ValueError('Correction / Re-Test / Evidence / Re-Review did not complete; Cycle diagnostics retained.')
            output = replace(output, review=cycle.re_review)
            # A new Review needs new explicit safety inputs before another Cycle.
            return self._finish(self._route(output))
        except Exception as exc:
            return self._finish(replace(output, success=False, stop_reason=f'{type(exc).__name__}: {exc}'))
