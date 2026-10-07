"""Existing Phase 7 components end-to-end through the T4 adapter, offline."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from test_plan_workflow import flow
from test_human_control_workflows import control
from test_execute_to_test_state_e2e import JsonlCodexRunner
from test_git_repository_state_provider import make_clean_repository, run_git
from test_review_workflow import approved_response
from test_review_implementation import response
from test_classify_review_result import evaluation
from application.codex_implementation_adapter import CodexImplementationAdapter
from application.execute_implementation import ExecuteImplementationUseCase
from application.implementation_workflow import (
    ImplementationWorkflowUseCase, ImplementationWorkflowInput, InitialTddApplicability)
from application.evidence_workflow import EvidenceWorkflowUseCase
from application.implementation_evidence import EvidenceScope
from application.review_workflow import ReviewWorkflowUseCase
from application.review_with_retry import ReviewWithRetryUseCase
from application.review_retry import RetryAuthorization
from application.final_approval_workflow import FinalApprovalWorkflowUseCase, HumanFinalDecisionInput
from core.ai.ai_service import AIService
from core.ai.ai_response import AIResponse
from infrastructure.codex_jsonl_parser import parse_codex_jsonl
from infrastructure.git_implementation_preparation import GitImplementationPreparation
from infrastructure.git_repository_state_provider import GitRepositoryStateProvider
from infrastructure.git_cli_merge_service import GitCliMergeService
from infrastructure.json_command_trace_repository import JsonCommandTraceRepository
from infrastructure.json_test_execution_record_repository import JsonTestExecutionRecordRepository
from infrastructure.json_test_execution_recorder import JsonTestExecutionRecorder
from infrastructure.json_test_state_provider import JsonTestStateProvider
from infrastructure.json_implementation_evidence_repository import JsonImplementationEvidenceRepository
from infrastructure.json_merge_retry_repository import JsonMergeRetryRepository
from human_control.application_adapter import ApplicationAdapter, ApplicationPorts, DelegatedInputs


@pytest.fixture
def connected(control):
    c = control
    root, base = make_clean_repository(c.f.tmp_path)
    c.service.record_references(c.project.project_id, c.work.workflow_id,
                                {'repository': root, 'implementation_target': root})
    runner = Mock()
    def run(**kwargs):
        (root / 'source.py').write_text('value = 1\n', encoding='utf-8')
        (root / 'test_source.py').write_text('assert 1 == 1\n', encoding='utf-8')
        run_git(root, 'add', 'source.py', 'test_source.py')
        return JsonlCodexRunner().run(**kwargs)
    runner.run.side_effect = run
    records = c.f.tmp_path / 'records'
    recorder = JsonTestExecutionRecorder(trace_repository=JsonCommandTraceRepository(records),
        record_repository=JsonTestExecutionRecordRepository(records))
    implementation = Mock(wraps=ImplementationWorkflowUseCase(c.f.repo, GitImplementationPreparation(),
        ExecuteImplementationUseCase(c.f.repo, CodexImplementationAdapter(runner, trace_parser=parse_codex_jsonl), recorder),
        JsonTestStateProvider))
    evidence_repo = JsonImplementationEvidenceRepository(c.f.tmp_path / 'evidence')
    evidence = Mock(wraps=EvidenceWorkflowUseCase(c.f.repo, evidence_repo,
        GitRepositoryStateProvider, JsonTestStateProvider))
    ai = Mock()
    ai.run.side_effect = lambda request: (approved_response(request)
        if request.prompt.startswith('# Review Result Evaluation')
        else AIResponse(json.dumps(response()), True))
    review = Mock(wraps=ReviewWorkflowUseCase(c.f.repo, evidence_repo,
        GitRepositoryStateProvider, JsonTestStateProvider,
        ReviewWithRetryUseCase(AIService(ai), lambda op, failure: RetryAuthorization())))
    git = Mock(wraps=GitCliMergeService(root))
    final = Mock(wraps=FinalApprovalWorkflowUseCase(git, c.f.repo, evidence_repo, JsonMergeRetryRepository))
    ports = ApplicationPorts(c.entry, c.plans, implementation, evidence, review, final)
    adapter = ApplicationAdapter(c.service, c.project.project_id, c.work.workflow_id, ports)
    def execution_inputs(plan):
        record = plan.approval_result.approval_record
        return ImplementationWorkflowInput(plan, uuid4(), root, 'impl/t4',
            InitialTddApplicability(plan.plan_path, record['approval_id'], record['artifact_hash'],
                hashlib.sha256(plan.prompt_result.codex_prompt.encode('utf-8')).hexdigest(), True))
    inputs = DelegatedInputs(replace(c.f.prompt, implementation_target_path=root), execution_inputs,
        EvidenceScope(('source.py', 'test_source.py'), ('*.py',), ()),
        (root / 'source.py',), (root / 'test_source.py',), 'BATCH')
    return SimpleNamespace(**locals())


def test_delegated_normal_path_reaches_final_human_gate_without_next_clicks(connected):
    x = connected
    assert x.adapter.start(x.c.f.generation).success
    result = x.adapter.decide_plan(x.c.f.decision, x.inputs)
    assert result.success, result.reason
    assert result.waiting_for_human
    waiting = result.outputs[-1]
    assert waiting.waiting_for_human and waiting.target.succeeded
    assert not waiting.completed
    for port, method in ((x.implementation, 'execute'), (x.evidence, 'execute'),
                         (x.review, 'start'), (x.final, 'start')):
        getattr(port, method).assert_called_once()
    x.git.merge.assert_not_called()
    refs = x.c.repository.artifact_references(x.c.work.workflow_id)
    for role in ('test_execution_record', 'codex_prompt', 'evidence', 'git_diff', 'review_snapshot', 'final_snapshot'):
        assert Path(refs[role]).is_file(), role
    trace = x.adapter.trace()
    assert trace.success and not trace.completed, trace.diagnostics
    assert trace.current_state['status'] == 'final_approval_pending'


def test_plan_repository_change_is_handed_to_human_without_next_stage(connected):
    from infrastructure.plan_codex_runner import PlanCodexRunner
    from test_plan_codex_runner import completed
    x = connected
    executor = Mock()
    def execute(*args, **kwargs):
        (x.root / 'tracked.txt').write_text('changed')
        return completed()
    executor.run.side_effect = execute
    x.c.f.use_case._generation._ai_service = AIService(PlanCodexRunner(executor, x.root, lambda path: None))
    result = x.adapter.start(x.c.f.generation)
    assert not result.success and result.waiting_for_human
    assert 'tracked.txt' in result.reason
    assert not x.c.f.plan_path.exists()
    assert json.loads(x.c.f.state.read_text())['status'] == 'plan_generating'
    x.implementation.execute.assert_not_called()
    x.evidence.execute.assert_not_called()
    x.review.start.assert_not_called()
    x.final.start.assert_not_called()


def test_final_return_retains_existing_route_without_auto_reexecution(connected):
    x = connected
    x.adapter.start(x.c.f.generation)
    result = x.adapter.decide_plan(x.c.f.decision, x.inputs)
    assert result.success, result.reason
    decision = HumanFinalDecisionInput('Plan Revision', 'Human requests another Plan')
    returned = x.adapter.decide_final(decision)
    assert returned.success and returned.waiting_for_human, returned.reason
    assert not returned.outputs[-1].completed
    assert returned.outputs[-1].routing is not None
    assert json.loads(x.c.f.state.read_text())['status'] == 'final_approval_pending'
    x.git.merge.assert_not_called()
    x.c.plans.generate.assert_called_once()
    assert not x.adapter.decide_final(decision).success


@pytest.mark.parametrize('missing', ['scope', 'source_selection', 'mode', 'repository', 'tdd', 'foreign_upstream'])
def test_missing_or_non_unique_execution_inputs_stop_before_implementation(connected, missing):
    x = connected
    inputs = x.inputs
    if missing == 'scope':
        inputs = replace(inputs, approved_scope=None)
    elif missing == 'source_selection':
        inputs = replace(inputs, source_paths=None)
    elif missing == 'mode':
        inputs = replace(inputs, review_mode=None)
    elif missing == 'repository':
        inputs = replace(inputs, implementation=lambda plan: replace(x.execution_inputs(plan), repository=x.c.f.tmp_path))
    elif missing == 'tdd':
        inputs = replace(inputs, implementation=lambda plan: None)
    else:
        inputs = replace(inputs, implementation=lambda plan: replace(x.execution_inputs(plan),
            upstream=replace(plan, entry=replace(plan.entry, request=replace(plan.entry.request,
                state_file=x.c.f.tmp_path / 'foreign-state.json')))))
    x.adapter.start(x.c.f.generation)
    stopped = x.adapter.decide_plan(x.c.f.decision, inputs)
    assert not stopped.success and stopped.waiting_for_human and stopped.reason
    x.implementation.execute.assert_not_called()
    x.runner.run.assert_not_called()
    x.evidence.execute.assert_not_called()
    x.review.start.assert_not_called()


def test_invalid_tdd_facts_are_validated_by_phase7(connected):
    x = connected
    def invalid(plan):
        request = x.execution_inputs(plan)
        return replace(request, tdd=replace(request.tdd, tdd_required=None))
    x.adapter.start(x.c.f.generation)
    stopped = x.adapter.decide_plan(x.c.f.decision, replace(x.inputs, implementation=invalid))
    assert not stopped.success
    x.implementation.execute.assert_called_once()
    x.runner.run.assert_not_called()
    x.evidence.execute.assert_not_called()


def test_human_review_is_not_final_approval_or_an_automatic_correction(connected):
    x = connected
    original = x.ai.run.side_effect
    def run(request):
        if request.prompt.startswith('# Review Result Evaluation'):
            data = evaluation('HUMAN_REVIEW_REQUIRED')
            data['references'] = ['review.prepared.review_input.implementation_plan.content']
            data['human_questions'] = ['Human must clarify the behavior']
            return AIResponse(json.dumps(data), True)
        return original(request)
    x.ai.run.side_effect = run
    x.adapter.start(x.c.f.generation)
    result = x.adapter.decide_plan(x.c.f.decision, x.inputs)
    assert result.success and result.waiting_for_human, result.reason
    assert result.outputs[-1].waiting_for_human
    x.final.start.assert_not_called()
    x.review.correct.assert_not_called()


def test_index_persistence_failure_retains_actual_output_and_stops_next_stage(connected, monkeypatch):
    x = connected
    x.adapter.start(x.c.f.generation)
    monkeypatch.setattr(x.c.repository, 'set_artifact_references', Mock(side_effect=OSError('disk full')))
    result = x.adapter.decide_plan(x.c.f.decision, x.inputs)
    assert not result.success and 'disk full' in result.reason
    assert result.outputs[-1].success
    x.evidence.execute.assert_not_called()


def test_explicit_final_approval_reuses_phase7_merge_and_completion(connected):
    x = connected
    original = x.runner.run.side_effect
    def committed(**kwargs):
        output = original(**kwargs)
        run_git(x.root, 'commit', '-m', 'Disposable T4 implementation')
        return output
    x.runner.run.side_effect = committed
    x.adapter.start(x.c.f.generation)
    waiting = x.adapter.decide_plan(x.c.f.decision, x.inputs)
    assert waiting.success, waiting.reason
    x.git.merge.assert_not_called()
    result = x.adapter.decide_final(HumanFinalDecisionInput(
        'Final Approval', 'Human accepts this exact target', 'final-t4', '2026-10-02T12:00:00+09:00'))
    assert result.success and not result.waiting_for_human, result.reason
    completed = result.outputs[-1]
    assert completed.completed and completed.completion.completed
    assert completed.merge.result.verification.verified
    x.git.merge.assert_called_once()
    assert run_git(x.root, 'branch', '--show-current') == 'developer'
    assert x.adapter.trace().completed


def test_prompt_persistence_failure_never_starts_implementation(connected):
    x = connected
    prompt = Path(x.c.repository.artifact_references(x.c.work.workflow_id)['codex_prompt'])
    prompt.write_text('Existing Artifact')
    x.adapter.start(x.c.f.generation)
    result = x.adapter.decide_plan(x.c.f.decision, x.inputs)
    assert not result.success
    assert prompt.read_text() == 'Existing Artifact'
    x.implementation.execute.assert_not_called()


def test_formal_reference_changed_after_start_never_receives_human_decision(connected):
    x = connected
    x.adapter.start(x.c.f.generation)
    x.c.repository.set_artifact_reference(x.c.work.workflow_id, 'plan', str(x.c.f.tmp_path / 'foreign-plan.md'))
    result = x.adapter.decide_plan(x.c.f.decision, x.inputs)
    assert not result.success and 'references changed' in result.reason
    x.c.plans.decide.assert_not_called()
    x.implementation.execute.assert_not_called()


def test_changed_specification_remains_visible_in_read_only_trace(control):
    c = control
    assert c.adapter.start(c.f.generation).success
    c.f.spec.write_text('Modified after entry')
    trace = c.adapter.trace()
    assert not trace.completed
    assert trace.current_state['status'] == 'plan_approval_pending'
