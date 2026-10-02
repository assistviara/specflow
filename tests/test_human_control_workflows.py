"""T4 boundaries: real SQLite, real Phase 7 Entry / Plan, offline AI."""
from dataclasses import replace
import hashlib
import json
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from application.workflow_entry import WorkflowEntryUseCase
from human_control.projects import ProjectService
from human_control.sqlite_repository import HumanControlRepository
from human_control.workflows import WorkflowService, WorkflowBoundaryError
from human_control.application_adapter import ApplicationAdapter, ApplicationPorts
from test_plan_workflow import flow
from test_human_control_projects import confirm_all


@pytest.fixture
def control(flow):
    f = flow
    # Phase 7 fixture has already entered; supply a fresh formal start State.
    f.state.write_text('{"status": "specification_ready"}')
    f.history = f.tmp_path / 'new-history'
    f.generation = replace(f.generation, state_history_dir=f.history,
        project_metadata=dict(project_name='Project', target_path=str(f.tmp_path),
                              project_description='Explicit description', project_version='1'))
    f.decision = replace(f.decision, state_history_dir=f.history)
    f.prompt = replace(f.prompt, state_history_dir=f.history)
    f.revision = replace(f.revision, state_history_dir=f.history)
    for field in ('constitution_path', 'principles_path', 'decisions_path',
                  'implementation_plan_template_path', 'template_path'):
        getattr(f.generation, field).write_text('Explicit formal input')
    f.prompt.template_path.write_text('Prompt template')
    f.revision.revision_template_path.write_text('Revision template')
    db = f.tmp_path / 'control.sqlite3'
    HumanControlRepository.initialize(db)
    repository = HumanControlRepository(db)
    projects = ProjectService(repository)
    project = projects.create('Project')
    confirm_all(projects, project)
    service = WorkflowService(repository)
    refs = dict(constitution=f.generation.constitution_path,
        principles=f.generation.principles_path, decisions=f.generation.decisions_path,
        plan_template=f.generation.implementation_plan_template_path,
        plan_prompt_template=f.generation.template_path, prompt_template=f.prompt.template_path,
        revision_template=f.revision.revision_template_path, plan=f.plan_path,
        repository=f.tmp_path, implementation_target=f.prompt.implementation_target_path,
        codex_prompt=f.tmp_path / 'codex-prompt.md',
        review_dir=f.tmp_path / 'review', final_dir=f.tmp_path / 'final')
    work = service.register(project.project_id, 'New work', f.spec,
        hashlib.sha256(f.spec.read_bytes()).hexdigest(), 'spec-1', f.state, f.history,
        refs, human_confirmed=True)
    entry = Mock(wraps=WorkflowEntryUseCase(f.repo))
    plans = Mock(wraps=f.use_case)
    ports = ApplicationPorts(entry, plans, Mock(), Mock(), Mock(), Mock())
    adapter = ApplicationAdapter(service, project.project_id, work.workflow_id, ports)
    return SimpleNamespace(**locals())


def test_entry_uses_actual_approval_and_automatically_generates_plan(control):
    c = control
    result = c.adapter.start(c.f.generation)
    assert result.success and result.waiting_for_human
    assert len(result.outputs) == 2
    entry, plan = result.outputs
    assert entry.approval_validation.is_valid and plan.success
    assert plan.approval_result is None
    assert c.f.plan_path.is_file()
    c.entry.execute.assert_called_once()
    assert c.entry.execute.call_args.args[0].specification_approval_id == 'spec-1'
    c.ports.implementation.execute.assert_not_called()
    assert json.loads(c.f.state.read_text())['status'] == 'plan_approval_pending'
    assert c.repository.get_workflow(c.work.workflow_id) == c.work


@pytest.mark.parametrize('failure', ['modified_specification', 'hash_mismatch', 'missing_specification',
    'missing_approval', 'invalid_approval', 'stale_approval', 'approval_target', 'ownership',
    'missing_input', 'ambiguous_input', 'state_missing', 'constitution_pending'])
def test_unsafe_entry_never_starts_plan_or_downstream(control, failure):
    c = control
    request = c.f.generation
    if failure == 'modified_specification':
        c.f.spec.write_text('Changed after approval')
    elif failure == 'hash_mismatch':
        with c.repository._connection() as db:
            db.execute('UPDATE workflows SET specification_hash = ?', ('0' * 64,))
    elif failure == 'missing_specification':
        c.f.spec.unlink()
    elif failure in ('invalid_approval', 'stale_approval', 'approval_target'):
        record = c.f.repo.get('spec-1')
        field, value = {'invalid_approval': ('decision', 'rejected'),
            'stale_approval': ('artifact_hash', '0' * 64),
            'approval_target': ('artifact_path', str(c.f.tmp_path / 'another.md'))}[failure]
        c.f.repo.save({**record, field: value})
    elif failure == 'missing_approval':
        (c.f.repo.approvals_dir / 'spec-1.json').unlink()
    elif failure == 'ownership':
        c.adapter = ApplicationAdapter(c.service, uuid4(), c.work.workflow_id, c.ports)
    elif failure == 'missing_input':
        request.constitution_path.unlink()
    elif failure == 'ambiguous_input':
        request = replace(request, specification_path=[c.f.spec, c.f.spec])
    elif failure == 'state_missing':
        c.f.state.unlink()
    else:
        c.projects.update_constitution(c.project.project_id, 'purpose', 'Needs confirmation')
    result = c.adapter.start(request)
    assert not result.success and result.waiting_for_human and result.reason
    assert result.required_human_action
    c.plans.generate.assert_not_called()
    c.ports.implementation.execute.assert_not_called()
    assert not c.f.plan_path.exists()
    if failure in ('missing_approval', 'invalid_approval', 'stale_approval', 'approval_target'):
        c.entry.execute.assert_called_once()
        assert result.outputs[0].failures


def test_text_and_index_cannot_create_approval(control):
    c = control
    c.f.spec.write_text('Human Approved')
    with c.repository._connection() as db:
        db.execute('UPDATE workflows SET specification_hash = ?',
                   (hashlib.sha256(c.f.spec.read_bytes()).hexdigest(),))
    result = c.adapter.start(c.f.generation)
    assert not result.success
    c.entry.execute.assert_called_once()
    c.plans.generate.assert_not_called()


def test_cross_workflow_storage_alias_blocks_before_entry(control):
    c = control
    other = c.projects.create('Other')
    c.repository.add_workflow(replace(c.work, workflow_id=uuid4(), project_id=other.project_id,
                                     state_path=str(c.f.state.parent / '.' / c.f.state.name)))
    result = c.adapter.start(c.f.generation)
    assert not result.success
    c.entry.execute.assert_not_called()


def test_registration_requires_human_and_preserves_formal_bytes(control):
    c = control
    before = c.f.state.read_bytes()
    with pytest.raises(WorkflowBoundaryError):
        c.service.register(c.project.project_id, 'Unconfirmed', c.f.spec, c.work.specification_hash,
            'spec-1', c.f.tmp_path / 'other-state', c.f.tmp_path / 'other-history', {},
            human_confirmed=False)
    assert len(c.repository.list_workflows(c.project.project_id)) == 1
    assert c.f.state.read_bytes() == before


def test_index_write_failure_starts_nothing(control, monkeypatch):
    c = control
    monkeypatch.setattr(c.repository, 'register_workflow', Mock(side_effect=OSError('index failed')))
    with pytest.raises(OSError, match='index failed'):
        c.service.register(c.project.project_id, 'New', c.f.spec, c.work.specification_hash,
            'spec-1', c.f.tmp_path / 'other-state', c.f.tmp_path / 'other-history', {},
            human_confirmed=True)
    c.entry.execute.assert_not_called()


def test_no_reentry_or_caller_forged_output(control):
    c = control
    assert c.adapter.start(c.f.generation).success
    assert not c.adapter.start(c.f.generation).success
    c.entry.execute.assert_called_once()
    assert not ApplicationAdapter(c.service, c.project.project_id, c.work.workflow_id,
                                 c.ports).decide_plan(c.f.decision).success


def test_existing_plan_decision_validation_and_revision_are_reused(control):
    c = control
    c.adapter.start(c.f.generation)
    invalid = c.adapter.decide_plan(replace(c.f.decision, human_decision='AI approved'))
    assert not invalid.success
    c.ports.implementation.execute.assert_not_called()


def test_plan_revision_retains_original_artifact_and_requires_new_approval(control):
    from core.ai.ai_response import AIResponse
    c = control
    c.adapter.start(c.f.generation)
    original = c.f.plan_path.read_bytes()
    returned = c.adapter.decide_plan(replace(c.f.decision, human_decision='revision_requested', comment='Fix scope'))
    assert returned.success
    c.f.plan_ai.run.return_value = AIResponse('### REVISED_IMPLEMENTATION_PLAN\n# Revised Plan\n'
        '### CHANGES\nScope fixed\n### PREVIOUS_VERSION_CORRESPONDENCE\nReplaces original', True)
    revised = c.f.tmp_path / 'revised-plan.md'
    result = c.adapter.revise_plan(c.f.revision, revised)
    assert result.success and result.waiting_for_human, result.reason
    assert result.outputs[-1].approval_result is None
    assert c.f.plan_path.read_bytes() == original
    c.ports.implementation.execute.assert_not_called()


def test_missing_project_metadata_stops_before_entry(control):
    c = control
    result = c.adapter.start(replace(c.f.generation, project_metadata={}))
    assert not result.success
    c.entry.execute.assert_not_called()


def test_registration_reference_failure_rolls_back_index_without_artifact_io(control):
    c = control
    before = c.f.state.read_bytes()
    work = replace(c.work, workflow_id=uuid4())
    with pytest.raises(ValueError):
        c.repository.register_workflow(work, {'': 'invalid-role'})
    with pytest.raises(KeyError):
        c.repository.get_workflow(work.workflow_id)
    assert c.f.state.read_bytes() == before


@pytest.mark.parametrize('role', ['codex_prompt', 'review_dir', 'final_dir'])
def test_same_workflow_write_targets_cannot_overlap_history(control, role):
    c = control
    c.repository.set_artifact_reference(c.work.workflow_id, role, str(c.f.history))
    result = c.adapter.start(c.f.generation)
    assert not result.success
    c.entry.execute.assert_not_called()
