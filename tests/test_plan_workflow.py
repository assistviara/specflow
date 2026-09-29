import json
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from application.dto import (
    GenerateImplementationPlanInput, GenerateCodexPromptInput,
    RequestPlanApprovalInput, ReviseImplementationPlanInput,
)
from application.generate_implementation_plan import GenerateImplementationPlanUseCase
from application.request_plan_approval import RequestPlanApprovalUseCase
from application.revise_implementation_plan import ReviseImplementationPlanUseCase
from application.generate_codex_prompt import GenerateCodexPromptUseCase
from application.plan_workflow import PlanWorkflowUseCase
from application.workflow_entry import WorkflowEntryInput, WorkflowEntryUseCase
from core.approval_record_service import build_approval_record_from_artifact
from core.ai.ai_response import AIResponse
from core.prompt_builder import PromptResult
from infrastructure.json_approval_record_repository import JsonApprovalRecordRepository


@pytest.fixture
def flow(tmp_path):
    spec = tmp_path / 'spec.md'
    spec.write_bytes(b'# Specification\r\n')
    state = tmp_path / 'state.json'
    state.write_text('{"status": "specification_ready"}')
    history = tmp_path / 'history'
    repo = JsonApprovalRecordRepository(tmp_path / 'approvals')
    repo.save(build_approval_record_from_artifact(
        'spec-1', 'specification', str(spec), 'approved', '2026-09-26', '',
    ))
    entry = WorkflowEntryUseCase(repo).execute(WorkflowEntryInput(spec, 'spec-1', state, history))
    plan_generator = Mock()
    plan_generator.generate.return_value = PromptResult('Generate plan', [], [], [])
    plan_generator.generate_revision.return_value = PromptResult('Revise plan', [], [], [])
    plan_ai = Mock()
    plan_ai.run.return_value = AIResponse('# Plan\r\nHuman review required.', True)
    prompt_generator = Mock()
    prompt_generator.generate.return_value = PromptResult('Generate implementation prompt', [], [], [])
    prompt_ai = Mock()
    prompt_text = '\n'.join([
        '## Implementation Scope\nApproved scope', '## Allowed Changes\nApproved files',
        '## Forbidden Changes\nOther files', '## TDD Requirements',
        *[f'python -m infrastructure.specflow_test_wrapper --phase {phase} -- pytest'
          for phase in ('initial', 'target', 'full')],
        '## Completion Conditions\nTests pass', '## Stop Conditions\nUnclear scope',
        '## Required Execution Result Reporting\nReport results',
        '## Human Approval Required Conditions\nCritical change',
    ])
    prompt_ai.run.return_value = AIResponse(prompt_text, True)
    use_case = PlanWorkflowUseCase(
        repo, GenerateImplementationPlanUseCase(plan_generator, plan_ai),
        RequestPlanApprovalUseCase(repo), ReviseImplementationPlanUseCase(plan_generator, plan_ai),
        GenerateCodexPromptUseCase(repo, prompt_generator, prompt_ai),
    )
    plan_path = tmp_path / 'plan.md'
    generation = GenerateImplementationPlanInput(
        tmp_path / 'constitution', tmp_path / 'principles', spec, entry.approval_record,
        tmp_path / 'decisions', tmp_path / 'plan-template', {}, tmp_path / 'template', state, history,
    )
    decision = RequestPlanApprovalInput(plan_path, 'approved', 'Human decision', 'plan-1', '2026-09-26', state, history)
    prompt = GenerateCodexPromptInput(
        spec, 'spec-1', plan_path, 'plan-1', tmp_path, 'TDD', 'Complete', 'Stop', 'Report',
        tmp_path / 'prompt-template', state, history,
    )
    revision = ReviseImplementationPlanInput(plan_path, 'Fix scope', spec, None, tmp_path / 'revision-template', state, history)
    return SimpleNamespace(**locals())


def test_approved_generated_plan_is_handed_to_codex_prompt_generation(flow):
    draft = flow.use_case.generate(flow.entry, flow.generation, flow.plan_path)
    assert draft.success
    assert draft.current_state['status'] == 'plan_approval_pending'
    assert flow.plan_path.read_bytes() == flow.plan_ai.run.return_value.content.encode('utf-8')
    assert not (flow.repo.approvals_dir / 'plan-1.json').exists()
    flow.prompt_ai.run.assert_not_called()

    approved = flow.use_case.decide(draft, flow.decision)
    assert approved.success
    assert approved.current_state['status'] == 'plan_approved'
    result = flow.use_case.generate_prompt(approved, flow.prompt)
    assert result.success and result.prompt_result.prompt_usable
    assert result.current_state['status'] == 'implementation_ready'
    assert flow.prompt_generator.generate.call_args.kwargs['implementation_plan_path'] == flow.plan_path
    assert flow.repo.get('plan-1') == approved.approval_result.approval_record
    transitions = [json.loads(p.read_text()) for p in flow.history.glob('*.json')]
    assert len(transitions) == 5
    assert all(t['from_state'] != t['to_state'] for t in transitions)


def generate_draft(flow):
    return flow.use_case.generate(flow.entry, flow.generation, flow.plan_path)


def approve_draft(flow):
    return flow.use_case.decide(generate_draft(flow), flow.decision)


def test_saved_record_must_validate_before_plan_approved_transition(flow, monkeypatch):
    draft = generate_draft(flow)
    save = flow.repo.save
    monkeypatch.setattr(flow.repo, 'save', lambda record: save({**record, 'artifact_hash': 'corrupted'}))
    result = flow.use_case.decide(draft, flow.decision)
    assert not result.success
    assert result.current_state['status'] == 'plan_approval_pending'
    assert 'plan_approved' not in [json.loads(p.read_text())['to_state'] for p in flow.history.glob('*.json')]
    flow.prompt_ai.run.assert_not_called()


def test_failed_target_one_cannot_start_plan_generation(flow):
    result = flow.use_case.generate(replace(flow.entry, can_generate_plan=False), flow.generation, flow.plan_path)
    assert not result.success
    flow.plan_ai.run.assert_not_called()
    assert not flow.plan_path.exists()


def test_changed_specification_after_entry_blocks_generation(flow):
    flow.spec.write_text('Changed specification')
    result = generate_draft(flow)
    assert not result.success
    assert 'hash does not match' in result.stop_reason
    flow.plan_ai.run.assert_not_called()


@pytest.mark.parametrize('decision', [None, '', 'pending', 'reject', 'APPROVED'])
def test_missing_or_ambiguous_human_decision_never_approves(flow, decision):
    draft = generate_draft(flow)
    result = flow.use_case.decide(draft, replace(flow.decision, human_decision=decision))
    assert not result.success
    assert result.current_state['status'] == 'plan_approval_pending'
    assert not (flow.repo.approvals_dir / 'plan-1.json').exists()
    assert not flow.use_case.generate_prompt(result, flow.prompt).success
    flow.prompt_ai.run.assert_not_called()


def test_draft_is_not_approval_even_when_ai_claims_approved(flow):
    flow.plan_ai.run.return_value = AIResponse('# Plan\nAPPROVED by AI', True)
    draft = generate_draft(flow)
    assert draft.success and draft.approval_result is None
    result = flow.use_case.generate_prompt(draft, flow.prompt)
    assert not result.success
    flow.prompt_ai.run.assert_not_called()


def test_revision_preserves_old_artifact_and_requires_new_human_approval(flow):
    draft = generate_draft(flow)
    original = flow.plan_path.read_bytes()
    decision = flow.use_case.decide(draft, replace(flow.decision, human_decision='revision_requested', comment='Fix scope'))
    assert decision.success
    assert decision.current_state['status'] == 'plan_revision_requested'
    assert not flow.use_case.generate_prompt(decision, flow.prompt).success
    flow.plan_ai.run.return_value = AIResponse(
        '### REVISED_IMPLEMENTATION_PLAN\n# Revised Plan\n'
        '### CHANGES\nScope fixed\n### PREVIOUS_VERSION_CORRESPONDENCE\nReplaces original', True,
    )
    revised_path = flow.tmp_path / 'revised-plan.md'
    revised = flow.use_case.revise(decision, flow.revision, revised_path)
    assert revised.success and revised.approval_result is None
    assert revised.current_state['status'] == 'plan_approval_pending'
    assert flow.plan_path.read_bytes() == original
    assert revised_path.read_text() == '# Revised Plan'
    assert not flow.use_case.generate_prompt(revised, flow.prompt).success
    flow.prompt_ai.run.assert_not_called()
    approved = flow.use_case.decide(revised, replace(flow.decision, implementation_plan_path=revised_path, approval_id='plan-2'))
    result = flow.use_case.generate_prompt(approved, replace(flow.prompt, implementation_plan_path=revised_path, implementation_plan_approval_id='plan-2'))
    assert result.success
    assert flow.repo.get('plan-1')['decision'] == 'revision_requested'
    assert flow.repo.get('plan-2')['decision'] == 'approved'


def test_cancellation_stops_without_prompt_or_automatic_restart(flow):
    decision = flow.use_case.decide(generate_draft(flow), replace(flow.decision, human_decision='cancelled'))
    assert decision.success and decision.approval_result.cancelled
    assert decision.current_state['status'] == 'cancelled'
    assert not flow.use_case.generate_prompt(decision, flow.prompt).success
    assert not generate_draft(flow).success
    flow.prompt_ai.run.assert_not_called()
    assert flow.plan_ai.run.call_count == 1


@pytest.mark.parametrize('mode', ['changed_bytes', 'missing_record', 'wrong_path', 'wrong_hash', 'pending_record'])
def test_current_plan_must_match_saved_human_approval_before_prompt(flow, mode):
    approved = approve_draft(flow)
    original = flow.repo.get('plan-1')
    if mode == 'changed_bytes':
        flow.plan_path.write_bytes(b'Changed after approval')
    elif mode == 'missing_record':
        (flow.repo.approvals_dir / 'plan-1.json').unlink()
    else:
        field, value = {'wrong_path': ('artifact_path', 'other.md'), 'wrong_hash': ('artifact_hash', 'stale'),
                        'pending_record': ('decision', 'pending')}[mode]
        flow.repo.save({**original, field: value})
    result = flow.use_case.generate_prompt(approved, flow.prompt)
    assert not result.success
    assert result.current_state['status'] == 'plan_approved'
    flow.prompt_generator.generate.assert_not_called()
    flow.prompt_ai.run.assert_not_called()
    if mode == 'changed_bytes':
        assert flow.repo.get('plan-1') == original


@pytest.mark.parametrize('field', ['specification_path', 'implementation_plan_path', 'implementation_plan_approval_id', 'specification_approval_id', 'state_file', 'state_history_dir'])
def test_prompt_cannot_substitute_workflow_identity(flow, field):
    approved = approve_draft(flow)
    value = 'different-id' if field.endswith('_id') else flow.tmp_path / 'different'
    result = flow.use_case.generate_prompt(approved, replace(flow.prompt, **{field: value}))
    assert not result.success
    flow.prompt_ai.run.assert_not_called()


@pytest.mark.parametrize('mode', ['ai_failure', 'empty_draft', 'save_failure'])
def test_plan_generation_or_artifact_failure_is_not_success(flow, mode):
    path = flow.plan_path
    if mode == 'ai_failure':
        flow.plan_ai.run.return_value = AIResponse('', False, 'Plan generation failed')
    elif mode == 'empty_draft':
        flow.plan_ai.run.return_value = AIResponse(' ', True)
    else:
        path = flow.tmp_path / 'missing-parent' / 'plan.md'
    result = flow.use_case.generate(flow.entry, flow.generation, path)
    assert not result.success
    assert not path.exists()
    assert not flow.use_case.decide(result, flow.decision).success
    flow.prompt_ai.run.assert_not_called()


@pytest.mark.parametrize('mode', ['ai_failure', 'unusable_result', 'unready_template'])
def test_prompt_failure_never_reports_implementation_ready(flow, mode):
    approved = approve_draft(flow)
    if mode == 'ai_failure':
        flow.prompt_ai.run.return_value = AIResponse('', False, 'Prompt failed')
    elif mode == 'unusable_result':
        flow.prompt_ai.run.return_value = AIResponse('Unstructured result', True)
    else:
        flow.prompt_generator.generate.return_value = PromptResult('', ['missing'], [], [])
    result = flow.use_case.generate_prompt(approved, flow.prompt)
    assert not result.success and not result.prompt_result.prompt_usable
    assert result.current_state['status'] == 'implementation_prompt_generating'


def test_approval_repository_failure_keeps_pending(flow, monkeypatch):
    draft = generate_draft(flow)
    monkeypatch.setattr(flow.repo, 'save', Mock(side_effect=OSError('Approval save failed')))
    result = flow.use_case.decide(draft, flow.decision)
    assert not result.success
    assert result.current_state['status'] == 'plan_approval_pending'


@pytest.mark.parametrize('decision', ['approved', 'revision_requested', 'cancelled'])
def test_missing_saved_approval_keeps_pending(flow, monkeypatch, decision):
    draft = generate_draft(flow)
    monkeypatch.setattr(flow.repo, 'get', Mock(return_value=None))
    result = flow.use_case.decide(draft, replace(flow.decision, human_decision=decision))
    assert not result.success
    assert result.current_state['status'] == 'plan_approval_pending'


@pytest.mark.parametrize('mode', ['ai_failure', 'invalid_output', 'save_failure'])
def test_revision_failure_never_inherits_approval(flow, mode):
    decision = flow.use_case.decide(generate_draft(flow), replace(flow.decision, human_decision='revision_requested', comment='Fix scope'))
    path = flow.tmp_path / 'revised.md'
    if mode == 'ai_failure':
        flow.plan_ai.run.return_value = AIResponse('', False, 'Revision failed')
    elif mode == 'invalid_output':
        flow.plan_ai.run.return_value = AIResponse('Missing required sections', True)
    else:
        path = flow.tmp_path / 'absent' / 'revised.md'
        flow.plan_ai.run.return_value = AIResponse(
            '### REVISED_IMPLEMENTATION_PLAN\nNew plan\n### CHANGES\nChanges\n'
            '### PREVIOUS_VERSION_CORRESPONDENCE\nCorrespondence', True,
        )
    result = flow.use_case.revise(decision, flow.revision, path)
    assert not result.success
    assert not flow.use_case.generate_prompt(result, flow.prompt).success
    flow.prompt_ai.run.assert_not_called()
    assert flow.plan_path.exists()


def test_state_load_failure_cannot_start_generation(flow):
    flow.state.write_text('invalid json')
    result = generate_draft(flow)
    assert not result.success and result.current_state is None
    flow.plan_ai.run.assert_not_called()


@pytest.mark.parametrize('stage', ['generate', 'decide', 'revise', 'prompt'])
@pytest.mark.parametrize('save', ['save_current_state', 'save_state_transition_history'])
def test_state_and_history_failure_preserve_partial_state(flow, monkeypatch, stage, save):
    import application.state_transition as persistence

    if stage == 'generate':
        operation = lambda: generate_draft(flow)
        before, after = 'plan_generating', 'plan_approval_pending'
    elif stage == 'decide':
        draft = generate_draft(flow)
        operation = lambda: flow.use_case.decide(draft, flow.decision)
        before, after = 'plan_approval_pending', 'plan_approved'
    elif stage == 'revise':
        decision = flow.use_case.decide(generate_draft(flow), replace(flow.decision, human_decision='revision_requested', comment='Fix scope'))
        operation = lambda: flow.use_case.revise(decision, flow.revision, flow.tmp_path / 'revised.md')
        before, after = 'plan_revision_requested', 'plan_generating'
    else:
        approved = approve_draft(flow)
        operation = lambda: flow.use_case.generate_prompt(approved, flow.prompt)
        before, after = 'plan_approved', 'implementation_prompt_generating'
    history = {p.name: p.read_bytes() for p in flow.history.glob('*.json')}
    monkeypatch.setattr(persistence, save, Mock(side_effect=OSError(save)))
    result = operation()
    assert not result.success
    assert result.state_before['status'] == before
    expected = before if save == 'save_current_state' else after
    assert result.current_state['status'] == expected
    assert json.loads(flow.state.read_text())['status'] == expected
    assert {p.name: p.read_bytes() for p in flow.history.glob('*.json')} == history
    assert save in result.stop_reason
    flow.prompt_ai.run.assert_not_called()
