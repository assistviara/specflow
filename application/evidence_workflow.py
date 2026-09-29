from dataclasses import dataclass, replace
import hashlib
from pathlib import Path
from uuid import UUID

from application.collect_implementation_evidence import CollectImplementationEvidenceUseCase
from application.current_state_repository import load_current_state
from application.dto import CollectImplementationEvidenceInput, CollectImplementationEvidenceOutput
from application.implementation_evidence import EvidenceScope
from application.implementation_workflow import ImplementationWorkflowOutput
from application.prepare_review_input import PrepareReviewInputUseCase
from application.review_input import PrepareReviewInputInput, PrepareReviewInputOutput
from core.approval_validation import validate_approval_result


@dataclass(frozen=True)
class EvidenceWorkflowInput:
    upstream: ImplementationWorkflowOutput
    codex_prompt_path: Path
    # Existing caller-supplied Scope and code selections; never inferred from Diff.
    approved_scope: EvidenceScope | None
    source_paths: tuple[Path, ...]
    test_paths: tuple[Path, ...]


@dataclass(frozen=True)
class EvidenceWorkflowOutput:
    request: EvidenceWorkflowInput
    success: bool = False
    collection: CollectImplementationEvidenceOutput | None = None
    handoff: PrepareReviewInputOutput | None = None
    current_state: dict | None = None
    stop_reason: str | None = None


class EvidenceWorkflowUseCase:
    """Initial Implementation -> saved Evidence -> Review Input, without Review."""

    def __init__(self, approvals, evidence_repository, repository_state_provider_factory,
                 test_state_provider_factory):
        self._approvals = approvals
        self._evidence = evidence_repository
        self._repositories = repository_state_provider_factory
        self._tests = test_state_provider_factory

    def _approval(self, expected, path, kind):
        saved = self._approvals.get(expected['approval_id'])
        if saved != expected:
            raise ValueError(f'Saved {kind} approval identity changed.')
        validation = validate_approval_result(saved, str(path), kind)
        if not validation.is_valid:
            raise ValueError('; '.join(validation.validation_errors))

    def _validate(self, request):
        upstream = request.upstream
        execution, inp, prepared = upstream.execution, upstream.execution_input, upstream.prepared
        if (not upstream.success or upstream.stop_reason or execution is None or not execution.success
                or execution.stop_reason or execution.error_message or execution.critical_change_required
                or execution.technical_retry_required or inp is None or prepared is None
                or upstream.test_state is None or execution.implementation_result is None
                or execution.test_execution_record_path is None):
            raise ValueError('Successful Target 3 with Implementation / Test facts is required.')
        identity = upstream.request.implementation_id
        if not isinstance(identity, UUID) or execution.implementation_id != identity or inp.implementation_id != identity:
            raise ValueError('Implementation identity mismatch.')
        if (prepared.repository != upstream.request.repository.resolve()
                or inp.working_directory != prepared.repository
                or prepared.implementation_branch != upstream.request.implementation_branch):
            raise ValueError('Repository identity mismatch.')
        for field in ('base_branch', 'base_commit', 'implementation_branch'):
            expected = getattr(prepared, field)
            if not expected or getattr(inp, field) != expected or getattr(execution, field) != expected:
                raise ValueError(f'Implementation {field} identity mismatch.')
        plan = upstream.request.upstream
        if not plan.success or plan.stop_reason or not plan.prompt_result or not plan.prompt_result.success:
            raise ValueError('Approved Plan / Prompt is unavailable.')
        spec_path = plan.entry.request.specification_path
        spec_approval = plan.entry.approval_record
        plan_approval = plan.approval_result.approval_record
        if (inp.specification_path != spec_path or execution.specification_path != spec_path
                or inp.codex_prompt_specification_path != spec_path
                or plan.prompt_result.specification_path != spec_path
                or inp.implementation_plan_path != plan.plan_path
                or execution.implementation_plan_path != plan.plan_path
                or inp.codex_prompt_implementation_plan_path != plan.plan_path
                or plan.prompt_result.implementation_plan_path != plan.plan_path
                or inp.specification_approval_id != spec_approval['approval_id']
                or inp.implementation_plan_approval_id != plan_approval['approval_id']
                or inp.codex_prompt != plan.prompt_result.codex_prompt
                or not plan.prompt_result.prompt_usable):
            raise ValueError('Approved artifact identity mismatch.')
        self._approval(spec_approval, spec_path, 'specification')
        self._approval(plan_approval, plan.plan_path, 'implementation_plan')
        tdd = upstream.request.tdd
        if (tdd.plan_path != plan.plan_path or tdd.plan_approval_id != plan_approval['approval_id']
                or tdd.plan_hash != plan_approval['artifact_hash']
                or tdd.prompt_hash != hashlib.sha256(inp.codex_prompt.encode('utf-8')).hexdigest()
                or type(tdd.tdd_required) is not bool or inp.tdd_required != tdd.tdd_required
                or inp.no_tdd_reason != tdd.no_tdd_reason
                or (tdd.tdd_required and tdd.no_tdd_reason is not None)
                or (not tdd.tdd_required and (not isinstance(tdd.no_tdd_reason, str) or not tdd.no_tdd_reason.strip()))):
            raise ValueError('TDD applicability identity mismatch.')
        if request.codex_prompt_path.read_text(encoding='utf-8') != inp.codex_prompt:
            raise ValueError('Saved Prompt differs from Target 3 Prompt.')
        if (inp.state_file != plan.entry.request.state_file
                or inp.state_history_dir != plan.entry.request.history_dir
                or not upstream.current_state or upstream.current_state.get('status') != 'implementation_completed'
                or execution.current_state != 'implementation_completed'):
            raise ValueError('Target 3 completion State identity mismatch.')
        return inp

    def execute(self, request: EvidenceWorkflowInput) -> EvidenceWorkflowOutput:
        output = EvidenceWorkflowOutput(request)
        state_file = None
        try:
            inp = self._validate(request)
            state_file = inp.state_file
            state = load_current_state(state_file)
            output = replace(output, current_state=state)
            if state != request.upstream.current_state or state.get('status') != 'implementation_completed':
                raise ValueError('Current State differs from Target 3 completion.')
            repository = self._repositories(inp.working_directory)
            observed = repository.get_state(inp.base_commit)
            if (observed.unavailable_evidence or observed.branch != inp.implementation_branch
                    or observed.base_commit != inp.base_commit):
                raise ValueError('Repository facts unavailable or branch / base identity mismatch.')
            execution = request.upstream.execution
            tests = self._tests(record_path=execution.test_execution_record_path,
                                expected_implementation_id=inp.implementation_id)
            test_state = tests.get_state()
            if test_state != request.upstream.test_state or test_state.errors:
                raise ValueError('Test facts unavailable or changed since Target 3.')
            if inp.tdd_required or execution.implementation_result.test_required:
                for phase in ('target', 'full'):
                    if (getattr(test_state, f'{phase}_test_status'), getattr(test_state, f'{phase}_test_result')) != ('COMPLETED', 'PASS'):
                        raise ValueError(f'{phase} Test requirements are not satisfied.')
            if inp.tdd_required and (test_state.initial_test_status, test_state.initial_test_result) != ('COMPLETED', 'FAIL'):
                raise ValueError('Initial FAIL is not established.')
            if not inp.tdd_required and test_state.no_tdd_reason != inp.no_tdd_reason:
                raise ValueError('TDD non-applicability reason changed.')
            collected = CollectImplementationEvidenceUseCase(repository, tests, self._evidence).execute(
                CollectImplementationEvidenceInput(
                    base_branch=inp.base_branch, test_execution_record_path=execution.test_execution_record_path,
                    implementation_id=inp.implementation_id, implementation_kind='INITIAL', previous_evidence_id=None,
                    specification_path=inp.specification_path, specification_approval_id=inp.specification_approval_id,
                    implementation_plan_path=inp.implementation_plan_path,
                    implementation_plan_approval_id=inp.implementation_plan_approval_id,
                    codex_prompt_path=request.codex_prompt_path, codex_prompt=inp.codex_prompt,
                    implementation_branch=inp.implementation_branch, base_commit=inp.base_commit,
                    implementation_result=execution.implementation_result, approved_scope=request.approved_scope,
                ))
            output = replace(output, collection=collected)
            if (not collected.success or collected.implementation_evidence is None
                    or collected.evidence_path is None or collected.git_diff_path is None):
                raise ValueError(collected.error_message or 'Evidence generation / persistence failed.')
            # Phase 5 determines required Review information. PARTIAL alone is
            # not a Review Result; retain all missing facts and inconsistencies.
            if self._evidence.load(collected.evidence_id) != collected.implementation_evidence:
                raise ValueError('Saved Evidence differs from generated Evidence.')
            handoff = PrepareReviewInputUseCase(
                evidence_repository=self._evidence, approval_repository=self._approvals,
                repository_state_provider=repository,
                test_state_provider_factory=lambda path, identity: self._tests(
                    record_path=path, expected_implementation_id=identity),
            ).execute(PrepareReviewInputInput(
                inp.implementation_id, collected.evidence_id, inp.working_directory,
                request.source_paths, request.test_paths, collected.missing_evidence,
                collected.inconsistencies, collected.human_approval_required,
            ))
            output = replace(output, handoff=handoff)
            if (handoff.review_input is None or handoff.missing_information
                    or handoff.acquisition_errors or handoff.mismatches):
                raise ValueError('Complete consistent Review Input is not established.')
            if (handoff.review_input.evidence != collected.implementation_evidence
                    or handoff.review_input.repository_state != observed
                    or handoff.review_input.test_state != test_state):
                raise ValueError('Evidence / Repository / Test facts changed during handoff.')
            self._validate(request)
            final_state = load_current_state(state_file)
            if final_state != state:
                raise ValueError('Current State changed during handoff.')
            # Human Decision: Handoff completion does not start Review or write State / History.
            return replace(output, success=True, current_state=final_state)
        except Exception as exc:
            if state_file is not None:
                try:
                    output = replace(output, current_state=load_current_state(state_file))
                except Exception:
                    output = replace(output, current_state=None)
            return replace(output, stop_reason=f'{type(exc).__name__}: {exc}')
