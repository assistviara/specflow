from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path
from uuid import UUID

from application.codex_prompt_output_parser import parse_codex_prompt_output
from application.current_state_repository import load_current_state
from application.dto import ExecuteImplementationInput, ExecuteImplementationOutput
from application.execution_state_provider import TestState
from application.implementation_preparation import ImplementationPreparation, PreparedImplementation
from application.plan_workflow import PlanWorkflowOutput
from core.approval_validation import validate_approval_result


@dataclass(frozen=True)
class InitialTddApplicability:
    plan_path: Path
    plan_approval_id: str
    plan_hash: str
    prompt_hash: str
    tdd_required: bool | None
    no_tdd_reason: str | None = None


@dataclass(frozen=True)
class ImplementationWorkflowInput:
    upstream: PlanWorkflowOutput
    implementation_id: UUID
    repository: Path
    implementation_branch: str
    tdd: InitialTddApplicability


@dataclass(frozen=True)
class ImplementationWorkflowOutput:
    request: ImplementationWorkflowInput
    success: bool = False
    prepared: PreparedImplementation | None = None
    execution_input: ExecuteImplementationInput | None = None
    execution: ExecuteImplementationOutput | None = None
    test_state: TestState | None = None
    state_before: dict | None = None
    current_state: dict | None = None
    stop_reason: str | None = None


class ImplementationWorkflowUseCase:
    def __init__(self, approvals, preparation: ImplementationPreparation, execution,
                 test_state_provider_factory):
        self._approvals = approvals
        self._preparation = preparation
        self._execution = execution
        self._test_states = test_state_provider_factory

    def _validate_approval(self, expected, path, kind):
        saved = self._approvals.get(expected['approval_id'])
        if saved != expected:
            raise ValueError(f'Saved {kind} approval identity changed.')
        checked = validate_approval_result(saved, str(path), kind)
        if not checked.is_valid:
            raise ValueError('; '.join(checked.validation_errors))

    def execute(self, request: ImplementationWorkflowInput) -> ImplementationWorkflowOutput:
        output = ImplementationWorkflowOutput(request)
        state_file = request.upstream.entry.request.state_file
        try:
            upstream = request.upstream
            prompt = upstream.prompt_result
            approval = upstream.approval_result
            if (not upstream.success or upstream.stop_reason or not upstream.entry.can_generate_plan
                    or upstream.entry.failures or prompt is None or not prompt.success
                    or not prompt.prompt_usable or not prompt.codex_prompt
                    or approval is None or approval.decision != 'approved' or not approval.approval_valid):
                raise ValueError('Target 2 must provide an approved usable Implementation Prompt.')
            if (prompt.implementation_plan_path != upstream.plan_path
                    or prompt.specification_path != upstream.entry.request.specification_path):
                raise ValueError('Plan / Prompt artifact identity mismatch.')
            self._validate_approval(upstream.entry.approval_record, prompt.specification_path, 'specification')
            self._validate_approval(approval.approval_record, upstream.plan_path, 'implementation_plan')
            parse_codex_prompt_output(prompt.codex_prompt)
            tdd = request.tdd
            if (tdd.plan_path != upstream.plan_path
                    or tdd.plan_approval_id != approval.approval_record['approval_id']
                    or tdd.plan_hash != approval.approval_record['artifact_hash']
                    or tdd.prompt_hash != hashlib.sha256(prompt.codex_prompt.encode('utf-8')).hexdigest()):
                raise ValueError('TDD applicability is not bound to the approved Plan / Prompt.')
            if type(tdd.tdd_required) is not bool:
                raise ValueError('Explicit tdd_required is required; Runner TEST_REQUIRED is not its authority.')
            if tdd.tdd_required and tdd.no_tdd_reason is not None:
                raise ValueError('TDD required conflicts with a non-applicability reason.')
            if not tdd.tdd_required and (not isinstance(tdd.no_tdd_reason, str) or not tdd.no_tdd_reason.strip()):
                raise ValueError('Explicit TDD non-applicability reason is required.')
            state = load_current_state(state_file)
            output = replace(output, state_before=state, current_state=state)
            if state.get('status') != 'implementation_ready':
                raise ValueError('Current State must be implementation_ready.')
            prepared = self._preparation.prepare(request.repository, request.implementation_branch)
            output = replace(output, prepared=prepared)
            if (prepared.repository != request.repository.resolve() or prepared.base_branch != 'developer'
                    or prepared.implementation_branch != request.implementation_branch or not prepared.base_commit):
                raise ValueError('Prepared repository / branch / base identity mismatch.')
            # Revalidate after branch checkout, which can change artifact bytes.
            self._validate_approval(upstream.entry.approval_record, prompt.specification_path, 'specification')
            self._validate_approval(approval.approval_record, upstream.plan_path, 'implementation_plan')
            execution_input = ExecuteImplementationInput(
                prepared.base_branch, request.implementation_id, prompt.specification_path,
                upstream.entry.request.specification_approval_id, upstream.plan_path,
                approval.approval_record['approval_id'], prompt.codex_prompt,
                prompt.specification_path, upstream.plan_path, prepared.implementation_branch,
                prepared.base_commit, prepared.repository, state_file, upstream.entry.request.history_dir,
                tdd_required=tdd.tdd_required, no_tdd_reason=tdd.no_tdd_reason,
            )
            output = replace(output, execution_input=execution_input)
            execution = self._execution.execute(execution_input)
            output = replace(output, execution=execution)
            if execution.test_execution_record_path is not None:
                tests = self._test_states(record_path=execution.test_execution_record_path,
                                         expected_implementation_id=request.implementation_id).get_state()
                output = replace(output, test_state=tests)
            if not execution.success:
                raise ValueError(execution.stop_reason or execution.error_message or 'Implementation execution failed.')
            if execution.test_execution_record_path is None:
                raise ValueError('Verified Test Execution Record is required.')
            if tests.errors:
                raise ValueError('Test execution contains errors.')
            required = tdd.tdd_required or execution.implementation_result.test_required
            for phase in ('target', 'full'):
                status, result = getattr(tests, f'{phase}_test_status'), getattr(tests, f'{phase}_test_result')
                if (required and (status, result) != ('COMPLETED', 'PASS')) or status == 'ERROR' or result == 'FAIL':
                    raise ValueError(f'{phase} Test conditions are not satisfied.')
            if tdd.tdd_required:
                if (tests.initial_test_status, tests.initial_test_result) != ('COMPLETED', 'FAIL'):
                    raise ValueError('Required Initial FAIL is not established.')
                # The provider has verified record identity and trace hash.
                record = json.loads(execution.test_execution_record_path.read_text(encoding='utf-8'))
                events = [json.loads(line) for line in Path(record['command_trace_path']).read_text(encoding='utf-8').splitlines()]
                orders = {phase: [e['event_order'] for e in events if e['test_phase'] == phase]
                          for phase in ('initial', 'target', 'full')}
                if not (max(orders['initial']) < min(orders['target'])
                        and max(orders['target']) < min(orders['full'])):
                    raise ValueError('Initial / Target / Full test order is not established.')
            elif tests.no_tdd_reason != tdd.no_tdd_reason:
                raise ValueError('Recorded non-applicability reason differs from explicit input.')
            state = load_current_state(state_file)
            if state.get('status') != 'implementation_completed':
                raise ValueError('Implementation completion State is not established.')
            return replace(output, success=True, current_state=state)
        except Exception as exc:
            try:
                state = load_current_state(state_file)
            except Exception:
                state = None
            return replace(output, current_state=state, stop_reason=f'{type(exc).__name__}: {exc}')
