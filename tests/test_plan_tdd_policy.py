from dataclasses import replace
from unittest.mock import Mock

import pytest

from core.tdd_policy import TddPolicy
from core.plan_prompt_generator import PlanPromptGenerator
from core.prompt_builder import PromptResult
from core.ai.ai_response import AIResponse
from application.generate_implementation_plan import GenerateImplementationPlanUseCase
from test_plan_workflow import flow, approve_draft
from test_human_control_workflow_execution_ui import launch, hidden, preview, start, decision


@pytest.mark.parametrize('policy', [None, TddPolicy(False, 'rules'), TddPolicy(True, '')])
def test_invalid_policy_never_calls_generation_ai(flow, policy):
    f = flow
    use_case = GenerateImplementationPlanUseCase(f.plan_generator, f.plan_ai)
    before = f.state.read_bytes()
    with pytest.raises(ValueError):
        use_case.execute(replace(f.generation, tdd_policy=policy))
    f.plan_ai.run.assert_not_called()
    assert f.state.read_bytes() == before


@pytest.mark.parametrize('policy', [TddPolicy(True, 'Human rules'), TddPolicy(False, 'Human rules', 'Documentation only')])
def test_policy_reaches_real_generation_and_revision_prompt(flow, policy):
    f = flow
    generator = PlanPromptGenerator(Mock(load=Mock(return_value='document')),
        Mock(build=Mock(return_value=PromptResult('Plan', [], [], []))))
    values = vars(f.generation).copy()
    for key in ('specification_approval', 'state_file', 'state_history_dir'):
        values.pop(key)
    values['tdd_policy'] = policy
    values['project_metadata'] = dict(project_name='P', target_path=str(f.tmp_path),
                                      project_description='D', project_version='1')
    result = generator.generate(**values)
    assert policy.instruction() in result.content
    revision = generator.generate_revision(current_implementation_plan_path=f.plan_path,
        revision_request='Revise', specification_path=f.spec, related_information=None,
        template_path=f.revision.revision_template_path, tdd_policy=policy)
    assert policy.instruction() in revision.content
    if policy.required:
        assert 'Create tests -> confirm initial failure -> implement -> confirm success.' in result.content
    else:
        assert 'Documentation only' in result.content


@pytest.mark.parametrize('new_policy', [None, TddPolicy(False, 'Human rules', 'Documentation only')])
def test_revision_preserves_selected_policy_and_requires_reapproval(flow, new_policy):
    f = flow
    draft = f.use_case.generate(f.entry, f.generation, f.plan_path)
    waiting = f.use_case.decide(draft, replace(f.decision, human_decision='revision_requested', comment='Fix scope'))
    f.plan_ai.run.return_value = AIResponse(
        '### REVISED_IMPLEMENTATION_PLAN\n# Revised Plan\n'
        '### CHANGES\nScope fixed\n### PREVIOUS_VERSION_CORRESPONDENCE\nReplaces original', True)
    revised = f.use_case.revise(waiting, replace(f.revision, tdd_policy=new_policy), f.tmp_path / 'revised.md')
    assert revised.success, revised.stop_reason
    assert revised.tdd_policy == (new_policy or f.generation.tdd_policy)
    assert revised.approval_result is None
    assert f.plan_generator.generate_revision.call_args.kwargs['tdd_policy'] == revised.tdd_policy


@pytest.mark.parametrize('values', [{}, {'tdd_required': 'no', 'tdd_rules': 'TDD'}])
def test_start_without_decision_or_reason_does_not_call_ai(launch, values):
    x = launch
    data = hidden(preview(x), x.base + '/start')
    for key in ('tdd_required', 'tdd_rules', 'no_tdd_reason'):
        data.pop(key, None)
    data.update(values, human_confirmed='yes')
    response = x.client.post(x.base + '/start', data=data)
    assert response.status_code in (400, 409)
    x.factory.assert_not_called()
    assert not x.repo.list_workflows(x.project.project_id)


def test_approval_cannot_replace_generated_policy(launch):
    x = launch
    work, path, _ = start(x)
    response, _ = decision(x, path, 'approved', tdd_required='no', no_tdd_reason='changed')
    assert response.status_code == 400
    x.ports.plans.decide.assert_not_called()
    page = x.client.get(path).get_data(as_text=True)
    assert 'Plan TDD policy' in page and 'name="tdd_required"' not in page


def test_implementation_prompt_has_same_policy(flow):
    f = flow
    approved = approve_draft(f)
    result = f.use_case.generate_prompt(approved, f.prompt)
    assert result.success, result.stop_reason
    assert f.generation.tdd_policy.instruction() in f.prompt_generator.generate.call_args.kwargs['tdd_rules']
