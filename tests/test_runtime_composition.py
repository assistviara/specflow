"""Offline tests of the production wiring, never live AI or a development Git repo."""
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app import create_environment_app
from human_control import runtime_composition as composition
from human_control.sqlite_repository import HumanControlRepository
from application.technical_review_retry import TechnicalReviewRetryUseCase
from application.review_retry import ReviewAIOperation, ReviewOperationKind
from core.ai.ai_request import AIRequest
from core.ai.ai_response import AIResponse


@pytest.fixture
def env(tmp_path):
    result = {'SPECFLOW_OPENAI_MODEL': 'human-selected-model', 'OPENAI_API_KEY': 'test-only-secret'}
    for name in ('SPECFLOW_EXECUTION_REPOSITORY', 'SPECFLOW_APPROVALS_DIR',
                 'SPECFLOW_EVIDENCE_DIR', 'SPECFLOW_EXECUTION_RECORDS_DIR'):
        path = tmp_path / name
        path.mkdir()
        result[name] = str(path)
    db = tmp_path / 'control.sqlite3'
    HumanControlRepository.initialize(db)
    result['SPECFLOW_HUMAN_CONTROL_DB'] = str(db)
    return result


@pytest.mark.parametrize('name', ['SPECFLOW_OPENAI_MODEL', 'OPENAI_API_KEY',
    'SPECFLOW_EXECUTION_REPOSITORY', 'SPECFLOW_APPROVALS_DIR', 'SPECFLOW_EVIDENCE_DIR',
    'SPECFLOW_EXECUTION_RECORDS_DIR'])
@pytest.mark.parametrize('value', ['', '   '])
def test_missing_setting_stops_web_before_workflow_registration(env, name, value):
    env[name] = value
    app = create_environment_app(env)
    client = app.test_client()
    response = client.post(f'/control/projects/{uuid4()}/workflows/start')
    assert response.status_code == 503
    assert name in response.get_data(as_text=True)
    assert 'test-only-secret' not in response.get_data(as_text=True)
    assert app.extensions['human_execution'].factory is None
    assert not app.extensions['human_execution'].runs
    assert client.get('/').status_code != 503


@pytest.mark.parametrize('value', ['relative', 'missing'])
def test_invalid_directory_stops_without_creating_it(env, tmp_path, value):
    path = 'relative' if value == 'relative' else str(tmp_path / 'missing')
    env['SPECFLOW_EXECUTION_RECORDS_DIR'] = path
    with pytest.raises(ValueError, match='SPECFLOW_EXECUTION_RECORDS_DIR'):
        composition.ExecutionSettings.from_environment(env)
    assert not (tmp_path / 'missing').exists()


def test_production_ports_share_formal_stores_without_ai_git_or_writes(env, monkeypatch, tmp_path):
    client = Mock()
    create_client = Mock(return_value=client)
    monkeypatch.setattr('core.ai.openai_client_factory.OpenAIClientFactory.create', create_client)
    process = Mock(side_effect=AssertionError('No process during composition'))
    monkeypatch.setattr('subprocess.run', process)
    before = sorted(str(p) for p in tmp_path.rglob('*'))
    app = create_environment_app(env)
    create_client.assert_not_called()
    factory = app.extensions['human_execution'].factory
    workflows = Mock()
    workflows.binding.return_value = (None, {})
    work = SimpleNamespace(project_id=uuid4(), workflow_id=uuid4())
    ports = factory(workflows, work)
    for key, cls in [('entry', composition.WorkflowEntryUseCase), ('plans', composition.PlanWorkflowUseCase),
                     ('implementation', composition.ImplementationWorkflowUseCase),
                     ('evidence', composition.EvidenceWorkflowUseCase), ('review', composition.ReviewWorkflowUseCase),
                     ('final', composition.FinalApprovalWorkflowUseCase)]:
        assert isinstance(getattr(ports, key), cls)
        assert getattr(ports, key)._approvals is ports.entry._approvals
    assert ports.entry._approvals.approvals_dir == factory.settings.approvals
    assert ports.evidence._evidence is ports.review._evidence is ports.final._evidence
    assert ports.evidence._evidence._evidence_dir == factory.settings.evidence
    assert ports.final._git.get_repository_identity() == env['SPECFLOW_EXECUTION_REPOSITORY']
    recorder = ports.implementation._execution._test_execution_recorder
    assert recorder._trace_repository._evidence_dir == recorder._record_repository._evidence_dir == factory.settings.records
    assert ports.final._retry_repositories is composition.JsonMergeRetryRepository
    assert ports.review._reviewer._retry._ai_service._runner._model == env['SPECFLOW_OPENAI_MODEL']
    client.responses.create.assert_not_called()
    process.assert_not_called()
    assert before == sorted(str(p) for p in tmp_path.rglob('*'))
    continuity = app.extensions['human_continuity']
    assert continuity.projection_service.approvals.approvals_dir == factory.settings.approvals


def test_restart_factory_rejects_other_repository_before_client_creation(env, monkeypatch, tmp_path):
    create = Mock()
    monkeypatch.setattr(composition, 'create_openai_runner', create)
    factory = composition.ProductionFactory(composition.ExecutionSettings.from_environment(env))
    service = Mock()
    service.binding.return_value = (None, {'repository': tmp_path})
    with pytest.raises(ValueError, match='Repository'):
        factory(service, SimpleNamespace(project_id=uuid4(), workflow_id=uuid4()))
    create.assert_not_called()


def test_web_repository_mismatch_stops_before_plan_approval(env, tmp_path):
    app = create_environment_app(env)
    response = app.test_client().post(
        f'/control/projects/{uuid4()}/workflows/{uuid4()}/execution/decide',
        data={'human_decision': 'approved', 'repository': str(tmp_path)})
    assert response.status_code == 409
    assert 'Repository' in response.get_data(as_text=True)


def test_retry_callback_preserves_failure_and_does_not_retry():
    ai = Mock()
    ai.run.return_value = AIResponse('', False, 'temporary error is not safety evidence')
    retry = TechnicalReviewRetryUseCase(ai, composition.deny_review_retry)
    operation = ReviewAIOperation(uuid4(), ReviewOperationKind.BATCH, AIRequest('review'), None)
    result = retry.execute(operation)
    assert result.retry_count == 0
    assert result.final_attempt.response.success is False
    assert result.authorization.reason
    ai.run.assert_called_once()


def test_missing_settings_stop_final_post_but_allow_decision_get(env):
    env.pop('SPECFLOW_OPENAI_MODEL')
    client = create_environment_app(env).test_client()
    url = f'/control/projects/{uuid4()}/workflows/{uuid4()}/decisions'
    assert client.post(url + '/final').status_code == 503
    assert client.get(url).status_code != 503


def test_matching_restart_binding_and_client_failure_do_not_leak_credentials(env, monkeypatch):
    create = Mock(side_effect=RuntimeError('test-only-secret'))
    monkeypatch.setattr(composition, 'create_openai_runner', create)
    settings = composition.ExecutionSettings.from_environment(env)
    service = Mock()
    service.binding.return_value = (None, {'repository': settings.repository})
    with pytest.raises(ValueError, match='OpenAI client') as caught:
        composition.ProductionFactory(settings)(service,
            SimpleNamespace(project_id=uuid4(), workflow_id=uuid4()))
    assert 'test-only-secret' not in str(caught.value)
    create.assert_called_once_with(settings.model)


def test_final_post_rechecks_repository_even_for_live_adapter(env, tmp_path, monkeypatch):
    app = create_environment_app(env)
    runtime = app.extensions['human_control']
    p, w = uuid4(), uuid4()
    monkeypatch.setattr(runtime, 'target', Mock(return_value=(p, w)))
    repository = Mock()
    repository.artifact_references.return_value = {'repository': str(tmp_path)}
    monkeypatch.setattr(runtime, 'require_repository', Mock(return_value=repository))
    response = app.test_client().post(f'/control/projects/{p}/workflows/{w}/decisions/final')
    assert response.status_code == 409
    assert 'Repository' in response.get_data(as_text=True)
