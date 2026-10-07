"""Explicit, fixed production composition. Constructors perform no workflow work."""
from dataclasses import dataclass
from pathlib import Path

from application.workflow_entry import WorkflowEntryUseCase
from application.plan_workflow import PlanWorkflowUseCase
from application.generate_implementation_plan import GenerateImplementationPlanUseCase
from application.request_plan_approval import RequestPlanApprovalUseCase
from application.revise_implementation_plan import ReviseImplementationPlanUseCase
from application.generate_codex_prompt import GenerateCodexPromptUseCase
from application.codex_implementation_adapter import CodexImplementationAdapter
from application.execute_implementation import ExecuteImplementationUseCase
from application.implementation_workflow import ImplementationWorkflowUseCase
from application.evidence_workflow import EvidenceWorkflowUseCase
from application.review_workflow import ReviewWorkflowUseCase
from application.review_with_retry import ReviewWithRetryUseCase
from application.review_retry import RetryAuthorization
from application.final_approval_workflow import FinalApprovalWorkflowUseCase
from core.ai.ai_service import AIService
from core.ai.runner_builder import create_openai_runner
from core.ai.codex_runner import CodexRunner
from core.plan_prompt_generator import PlanPromptGenerator
from core.codex_prompt_generator import CodexPromptGenerator
from infrastructure.subprocess_command_executor import SubprocessCommandExecutor
from infrastructure.codex_jsonl_parser import parse_codex_jsonl
from infrastructure.plan_codex_runner import PlanCodexRunner
from infrastructure.git_implementation_preparation import GitImplementationPreparation
from infrastructure.git_repository_state_provider import GitRepositoryStateProvider
from infrastructure.git_cli_merge_service import GitCliMergeService
from infrastructure.json_approval_record_repository import JsonApprovalRecordRepository
from infrastructure.json_implementation_evidence_repository import JsonImplementationEvidenceRepository
from infrastructure.json_command_trace_repository import JsonCommandTraceRepository
from infrastructure.json_test_execution_record_repository import JsonTestExecutionRecordRepository
from infrastructure.json_test_execution_recorder import JsonTestExecutionRecorder
from infrastructure.json_test_state_provider import JsonTestStateProvider
from infrastructure.json_merge_retry_repository import JsonMergeRetryRepository
from human_control.application_adapter import ApplicationPorts


def deny_review_retry(operation, failure):
    return RetryAuthorization(reason='Safety evidence is unverified; automatic Review Retry is not authorized.')


@dataclass(frozen=True)
class ExecutionSettings:
    model: str
    repository: Path
    approvals: Path
    evidence: Path
    records: Path

    @classmethod
    def from_environment(cls, env):
        names = ('SPECFLOW_OPENAI_MODEL', 'SPECFLOW_EXECUTION_REPOSITORY',
                 'SPECFLOW_APPROVALS_DIR', 'SPECFLOW_EVIDENCE_DIR', 'SPECFLOW_EXECUTION_RECORDS_DIR')
        missing = [name for name in names if not env.get(name, '').strip()]
        if not env.get('OPENAI_API_KEY', '').strip():
            missing.append('OPENAI_API_KEY')
        if missing:
            raise ValueError('実行設定が未設定です: ' + ', '.join(missing))
        paths = []
        for name in names[1:]:
            path = Path(env[name])
            if not path.is_absolute() or not path.is_dir():
                raise ValueError(f'{name}: Humanが準備した既存directoryの絶対パスを指定してください。')
            paths.append(path.resolve())
        return cls(env[names[0]].strip(), *paths)

    def check_repository(self, value):
        path = Path(value)
        if not path.is_absolute() or path.resolve() != self.repository:
            raise ValueError('対象RepositoryがSPECFLOW_EXECUTION_REPOSITORYと一致しません。')


class ProductionFactory:
    def __init__(self, settings: ExecutionSettings):
        self.settings = settings

    def __call__(self, workflows, registered_workflow):
        # On restart, reject a formal/index target from another configured repository.
        _, refs = workflows.binding(registered_workflow.project_id, registered_workflow.workflow_id)
        if 'repository' in refs:
            self.settings.check_repository(refs['repository'])
        s = self.settings
        approvals = JsonApprovalRecordRepository(s.approvals)
        evidence = JsonImplementationEvidenceRepository(s.evidence)
        try:
            ai = AIService(create_openai_runner(s.model))
        except Exception:
            raise ValueError('OpenAI client構成に失敗しました。認証設定を確認してください。') from None
        generator = PlanPromptGenerator()
        plan_ai = AIService(PlanCodexRunner(SubprocessCommandExecutor(), s.repository,
                                           s.check_repository))
        plans = PlanWorkflowUseCase(approvals,
            GenerateImplementationPlanUseCase(generator, plan_ai, s.check_repository), RequestPlanApprovalUseCase(approvals),
            ReviseImplementationPlanUseCase(generator, ai),
            GenerateCodexPromptUseCase(approvals, CodexPromptGenerator(), ai))
        recorder = JsonTestExecutionRecorder(
            trace_repository=JsonCommandTraceRepository(s.records),
            record_repository=JsonTestExecutionRecordRepository(s.records))
        implementation = ImplementationWorkflowUseCase(approvals, GitImplementationPreparation(),
            ExecuteImplementationUseCase(approvals,
                CodexImplementationAdapter(CodexRunner(SubprocessCommandExecutor()),
                                           trace_parser=parse_codex_jsonl), recorder), JsonTestStateProvider)
        return ApplicationPorts(WorkflowEntryUseCase(approvals), plans, implementation,
            EvidenceWorkflowUseCase(approvals, evidence, GitRepositoryStateProvider, JsonTestStateProvider),
            ReviewWorkflowUseCase(approvals, evidence, GitRepositoryStateProvider, JsonTestStateProvider,
                                  ReviewWithRetryUseCase(ai, deny_review_retry)),
            FinalApprovalWorkflowUseCase(GitCliMergeService(s.repository), approvals, evidence,
                                        JsonMergeRetryRepository))
