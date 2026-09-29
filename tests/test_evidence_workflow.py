from pathlib import Path
from types import SimpleNamespace
from dataclasses import replace
import json
from unittest.mock import Mock
from uuid import uuid4

import pytest

from test_plan_workflow import flow
from test_implementation_workflow import implementation
from test_execute_to_test_state_e2e import JsonlCodexRunner
from test_git_repository_state_provider import run_git
from application.implementation_evidence import EvidenceScope
from infrastructure.git_repository_state_provider import GitRepositoryStateProvider
from infrastructure.json_implementation_evidence_repository import JsonImplementationEvidenceRepository
from infrastructure.json_test_state_provider import JsonTestStateProvider


@pytest.fixture
def evidence_flow(implementation):
    from application.evidence_workflow import EvidenceWorkflowInput, EvidenceWorkflowUseCase

    flow, request, runner, implementation_use_case, base = implementation
    def run(**kwargs):
        (request.repository / 'source.py').write_text('value = 1\n', encoding='utf-8')
        (request.repository / 'test_source.py').write_text('assert 1 == 1\n', encoding='utf-8')
        run_git(request.repository, 'add', 'source.py', 'test_source.py')
        return JsonlCodexRunner().run(**kwargs)
    runner.run.side_effect = run
    upstream = implementation_use_case.execute(request)
    assert upstream.success, upstream.stop_reason
    prompt_path = flow.tmp_path / 'prompt.md'
    prompt_path.write_text(request.upstream.prompt_result.codex_prompt, encoding='utf-8')
    repository = JsonImplementationEvidenceRepository(flow.tmp_path / 'evidence')
    evidence_request = EvidenceWorkflowInput(
        upstream, prompt_path, EvidenceScope(('source.py', 'test_source.py'), ('*.py',), ()),
        (Path('source.py'),), (Path('test_source.py'),),
    )
    use_case = EvidenceWorkflowUseCase(flow.repo, repository, GitRepositoryStateProvider, JsonTestStateProvider)
    return SimpleNamespace(**locals())


def test_successful_implementation_creates_saved_evidence_and_complete_review_handoff(evidence_flow):
    case = evidence_flow
    state_before = case.flow.state.read_bytes()
    history_before = {p.name: p.read_bytes() for p in case.flow.history.glob('*.json')}

    result = case.use_case.execute(case.evidence_request)

    assert result.success, result.stop_reason
    collected = result.collection
    assert collected.success and collected.evidence_path.is_file()
    assert collected.git_diff_path.is_file()
    saved = case.repository.load(collected.evidence_id)
    assert saved == collected.implementation_evidence
    assert saved.identity.implementation_id == case.request.implementation_id
    assert saved.identity.base_commit == case.base
    assert saved.verification.initial_test_result == 'FAIL'
    assert saved.verification.target_test_result == 'PASS'
    assert saved.verification.full_test_result == 'PASS'
    handoff = result.handoff
    assert not handoff.missing_information and not handoff.acquisition_errors and not handoff.mismatches
    inp = handoff.review_input
    assert all((inp.specification, inp.implementation_plan, inp.codex_prompt, inp.evidence,
                inp.sources, inp.saved_diff, inp.tests, inp.test_state))
    assert 'value = 1' in inp.sources[0].content
    assert 'source.py' in inp.saved_diff.content
    assert inp.evidence == saved
    assert inp.request.collection_inconsistencies == collected.inconsistencies
    assert result.current_state['status'] == 'implementation_completed'
    assert case.flow.state.read_bytes() == state_before
    assert {p.name: p.read_bytes() for p in case.flow.history.glob('*.json')} == history_before
    case.runner.run.assert_called_once()


def snapshot(case):
    return (case.flow.state.read_bytes(),
            {p.name: p.read_bytes() for p in case.flow.history.glob('*.json')},
            {p.name: p.read_bytes() for p in case.flow.repo.approvals_dir.glob('*.json')})


def stopped(case, request=None):
    before = snapshot(case)
    result = case.use_case.execute(request or case.evidence_request)
    assert not result.success and result.stop_reason
    assert snapshot(case) == before
    case.runner.run.assert_called_once()
    return result


@pytest.mark.parametrize('mode', [
    'failed', 'stop', 'no_execution', 'execution_failed', 'execution_error',
    'critical_change', 'retry', 'no_result', 'no_record', 'no_tests', 'no_prepared',
    'unknown_id', 'execution_id', 'input_id', 'repository', 'branch', 'base',
    'spec_path', 'plan_path', 'prompt', 'state_identity', 'completion_state', 'tdd',
])
def test_invalid_target_three_never_generates_evidence(evidence_flow, mode):
    case = evidence_flow
    upstream = case.upstream
    if mode == 'failed':
        upstream = replace(upstream, success=False)
    elif mode == 'stop':
        upstream = replace(upstream, stop_reason='Stopped')
    elif mode == 'no_execution':
        upstream = replace(upstream, execution=None)
    elif mode == 'no_tests':
        upstream = replace(upstream, test_state=None)
    elif mode == 'no_prepared':
        upstream = replace(upstream, prepared=None)
    elif mode == 'unknown_id':
        upstream = replace(upstream, request=replace(upstream.request, implementation_id=None))
    elif mode == 'repository':
        upstream = replace(upstream, prepared=replace(upstream.prepared, repository=case.flow.tmp_path))
    elif mode == 'completion_state':
        upstream = replace(upstream, current_state={'status': 'implementing'})
    elif mode in ('input_id', 'spec_path', 'plan_path', 'prompt', 'state_identity', 'tdd'):
        field, value = {
            'input_id': ('implementation_id', uuid4()),
            'spec_path': ('specification_path', case.flow.tmp_path / 'other.md'),
            'plan_path': ('implementation_plan_path', case.flow.tmp_path / 'other.md'),
            'prompt': ('codex_prompt', 'changed'),
            'state_identity': ('state_file', case.flow.tmp_path / 'other.json'),
            'tdd': ('tdd_required', False),
        }[mode]
        upstream = replace(upstream, execution_input=replace(upstream.execution_input, **{field: value}))
    else:
        field, value = {
            'execution_failed': ('success', False), 'execution_error': ('error_message', 'failed'),
            'critical_change': ('critical_change_required', True), 'retry': ('technical_retry_required', True),
            'no_result': ('implementation_result', None), 'no_record': ('test_execution_record_path', None),
            'execution_id': ('implementation_id', uuid4()), 'branch': ('implementation_branch', 'other'),
            'base': ('base_commit', 'other'),
        }[mode]
        upstream = replace(upstream, execution=replace(upstream.execution, **{field: value}))
    result = stopped(case, replace(case.evidence_request, upstream=upstream))
    assert result.collection is None
    assert not (case.flow.tmp_path / 'evidence').exists()


@pytest.mark.parametrize('mode', ['plan', 'specification', 'approval', 'prompt', 'record', 'trace', 'state'])
def test_changed_or_unreadable_saved_artifacts_stop(evidence_flow, mode):
    case = evidence_flow
    if mode == 'plan':
        case.flow.plan_path.write_text('Changed Plan', encoding='utf-8')
    elif mode == 'specification':
        case.flow.spec.write_text('Changed Specification', encoding='utf-8')
    elif mode == 'approval':
        (case.flow.repo.approvals_dir / 'plan-1.json').unlink()
    elif mode == 'prompt':
        case.prompt_path.write_text('Changed Prompt', encoding='utf-8')
    elif mode == 'record':
        case.upstream.execution.test_execution_record_path.unlink()
    elif mode == 'trace':
        record = json.loads(case.upstream.execution.test_execution_record_path.read_text(encoding='utf-8'))
        Path(record['command_trace_path']).write_text('changed', encoding='utf-8')
    else:
        case.flow.state.write_text('{broken', encoding='utf-8')
    assert stopped(case).collection is None


@pytest.mark.parametrize('mode', ['branch', 'base', 'diff', 'error'])
def test_observed_repository_failures_do_not_replace_saved_identity(evidence_flow, mode):
    case = evidence_flow
    provider = Mock(wraps=GitRepositoryStateProvider(case.request.repository))
    actual = provider.get_state(case.base)
    if mode == 'error':
        provider.get_state.side_effect = OSError('Repository unavailable')
    else:
        changes = {'branch': {'branch': 'other'}, 'base': {'base_commit': 'other'},
                   'diff': {'unavailable_evidence': ('git_diff',)}}[mode]
        provider.get_state.return_value = replace(actual, **changes)
    case.use_case._repositories = Mock(return_value=provider)
    original = case.upstream.prepared
    assert stopped(case).collection is None
    assert case.upstream.prepared == original


@pytest.mark.parametrize('mode', ['source_missing', 'tests_missing', 'source_escape', 'source_selection', 'test_selection'])
def test_incomplete_eight_inputs_stop_after_preserving_saved_evidence(evidence_flow, mode):
    case = evidence_flow
    request = case.evidence_request
    if mode == 'source_missing':
        (case.request.repository / 'source.py').unlink()
    elif mode == 'tests_missing':
        (case.request.repository / 'test_source.py').unlink()
    elif mode == 'source_escape':
        request = replace(request, source_paths=(case.flow.spec,))
    elif mode == 'source_selection':
        request = replace(request, source_paths=())
    else:
        request = replace(request, test_paths=())
    result = stopped(case, request)
    assert result.collection.success
    assert result.collection.evidence_path.exists()
    assert result.handoff.review_input is None
    assert result.handoff.missing_information


@pytest.mark.parametrize('mode', ['diff_save', 'evidence_save', 'load', 'saved_mismatch', 'generation'])
def test_evidence_failure_and_partial_save_are_visible(evidence_flow, monkeypatch, mode):
    case = evidence_flow
    if mode in ('diff_save', 'evidence_save', 'load'):
        method = {'diff_save': 'save_diff', 'evidence_save': 'save', 'load': 'load'}[mode]
        monkeypatch.setattr(case.repository, method, Mock(side_effect=OSError('storage failure')))
    elif mode == 'saved_mismatch':
        load = case.repository.load
        monkeypatch.setattr(case.repository, 'load', lambda key: replace(load(key), codex_summary=None))
    else:
        provider = GitRepositoryStateProvider(case.request.repository)
        actual = provider.get_state(case.base)
        wrapper = Mock()
        wrapper.get_state.side_effect = [actual, OSError('collection failed')]
        case.use_case._repositories = Mock(return_value=wrapper)
    result = stopped(case)
    assert result.collection is not None and result.handoff is None
    if mode == 'evidence_save':
        assert result.collection.implementation_evidence is not None
        assert result.collection.git_diff_path.is_file()
        assert result.collection.evidence_path is None
    elif mode in ('load', 'saved_mismatch'):
        assert result.collection.success and result.collection.evidence_path.exists()
    else:
        assert not result.collection.success


def test_runner_inconsistencies_and_optional_missing_facts_remain_visible(evidence_flow):
    case = evidence_flow
    result = case.use_case.execute(case.evidence_request)
    assert result.success, result.stop_reason
    assert result.collection.status == 'PARTIAL'
    assert 'warnings' in result.collection.missing_evidence
    assert result.collection.inconsistencies  # Report claims example.py; actual Git has source.py.
    assert result.handoff.review_input.request.collection_missing_evidence == result.collection.missing_evidence
    assert result.handoff.review_input.request.collection_inconsistencies == result.collection.inconsistencies
    assert result.collection.implementation_evidence.codex_summary.implementation_result == case.upstream.execution.implementation_result


def test_state_change_during_collection_stops_without_rollback(evidence_flow, monkeypatch):
    case = evidence_flow
    save = case.repository.save
    def save_and_change_state(evidence):
        path = save(evidence)
        case.flow.state.write_text('{"status": "cancelled"}', encoding='utf-8')
        return path
    monkeypatch.setattr(case.repository, 'save', save_and_change_state)
    result = case.use_case.execute(case.evidence_request)
    assert not result.success and result.current_state['status'] == 'cancelled'
    assert result.collection.evidence_path.exists()


def test_handoff_does_not_call_state_or_history_writers_or_review(evidence_flow, monkeypatch):
    from application import current_state_repository, state_transition_history, review_implementation
    def forbidden(*args, **kwargs):
        pytest.fail('Target 4 must not write State / History or execute Review')
    monkeypatch.setattr(current_state_repository, 'save_current_state', forbidden)
    monkeypatch.setattr(state_transition_history, 'save_state_transition_history', forbidden)
    monkeypatch.setattr(review_implementation.ReviewImplementationUseCase, 'execute', forbidden)
    assert evidence_flow.use_case.execute(evidence_flow.evidence_request).success


def test_unavailable_scope_keeps_existing_partial_contract_without_inference(evidence_flow):
    case = evidence_flow
    result = case.use_case.execute(replace(case.evidence_request, approved_scope=None))
    assert result.success, result.stop_reason
    assert result.collection.implementation_evidence.scope is None
    assert 'approved scope unavailable' in result.collection.missing_evidence
    assert result.handoff.review_input.evidence.scope is None


def test_partial_with_unavailable_required_test_result_cannot_complete_handoff(evidence_flow):
    case = evidence_flow
    tests = replace(case.upstream.test_state, unavailable_evidence=('full_test_result',))
    provider = Mock()
    provider.get_state.return_value = tests
    case.use_case._tests = Mock(return_value=provider)
    request = replace(case.evidence_request, upstream=replace(case.upstream, test_state=tests))
    result = stopped(case, request)
    assert result.collection.status == 'PARTIAL'
    assert 'test.full_test_result' in result.handoff.missing_information
    assert result.handoff.review_input is None


@pytest.mark.parametrize('mode', ['test_state', 'current_state'])
def test_changed_completion_facts_stop_before_collection(evidence_flow, mode):
    case = evidence_flow
    if mode == 'test_state':
        provider = Mock()
        provider.get_state.return_value = replace(case.upstream.test_state, full_test_result='FAIL')
        case.use_case._tests = Mock(return_value=provider)
    else:
        case.flow.state.write_text('{"status": "reviewing"}', encoding='utf-8')
    assert stopped(case).collection is None


@pytest.mark.parametrize('mode', ['diff', 'approval', 'evidence_identity'])
def test_post_save_handoff_validation_failure_preserves_diagnostics(evidence_flow, monkeypatch, mode):
    case = evidence_flow
    if mode == 'evidence_identity':
        load = case.repository.load
        count = 0
        def altered_load(key):
            nonlocal count
            count += 1
            saved = load(key)
            return saved if count == 1 else replace(saved, identity=replace(saved.identity, implementation_id=uuid4()))
        monkeypatch.setattr(case.repository, 'load', altered_load)
    else:
        save = case.repository.save
        def save_and_alter(evidence):
            path = save(evidence)
            if mode == 'diff':
                evidence.changes.git_diff_path.write_text('different diff', encoding='utf-8')
            else:
                (case.flow.repo.approvals_dir / 'plan-1.json').unlink()
            return path
        monkeypatch.setattr(case.repository, 'save', save_and_alter)
    # The injected storage fault may alter an Approval; Target 4 must not repair it.
    before_state = case.flow.state.read_bytes()
    result = case.use_case.execute(case.evidence_request)
    assert not result.success and result.stop_reason
    assert result.collection.success and result.collection.evidence_path.exists()
    assert result.handoff.mismatches or result.handoff.missing_information
    assert case.flow.state.read_bytes() == before_state
