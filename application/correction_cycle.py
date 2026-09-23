from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from application.correction_routing import CorrectionRoutingOutput
from application.dto import CollectImplementationEvidenceOutput
from application.execution_state_provider import TestState
from application.repository_state_provider import RepositoryState
from application.implementation_result_parser import ImplementationResult
from application.review_input import PrepareReviewInputOutput
from application.review_with_retry import ReviewRetryOutput


@dataclass(frozen=True)
class ReTestPlan:
    target_commands: tuple[str, ...]
    required_commands: tuple[str, ...]
    existing_commands: tuple[str, ...]
    full_commands: tuple[str, ...]
    behavior_change: bool

    def commands(self) -> tuple[tuple[str, str], ...]:
        return tuple((command, 'target') for command in (
            *self.target_commands, *self.required_commands, *self.existing_commands
        )) + tuple((command, 'full') for command in self.full_commands)


@dataclass(frozen=True)
class CorrectionCycleInput:
    routing: CorrectionRoutingOutput
    state_file: Path
    state_history_dir: Path
    artifact_dir: Path
    tests: ReTestPlan
    source_paths: tuple[Path, ...] | None = None
    test_paths: tuple[Path, ...] | None = None


@dataclass(frozen=True)
class CycleFailure:
    kind: str
    detail: str


@dataclass(frozen=True)
class CorrectionAttempt:
    instruction_index: int
    prompt_path: Path
    summary: str | None
    changed_files: tuple[str, ...]
    repository_state: RepositoryState | None
    failure: CycleFailure | None
    execution_result: ImplementationResult | None = None


@dataclass(frozen=True)
class CorrectionHistory:
    implementation_id: UUID
    routing: CorrectionRoutingOutput
    previous_evidence_id: UUID
    correction_count_before: int
    correction_count: int
    changed_files: tuple[str, ...] = ()
    attempts: tuple[CorrectionAttempt, ...] = ()
    prompt_artifact_path: Path | None = None
    test_execution_record_path: Path | None = None
    command_trace_path: Path | None = None
    test_state: TestState | None = None
    retest_result: ImplementationResult | None = None
    new_evidence_id: UUID | None = None
    failures: tuple[CycleFailure, ...] = ()


@dataclass(frozen=True)
class CorrectionCycleOutput:
    request: CorrectionCycleInput
    history: CorrectionHistory | None
    current_state: str | None
    history_path: Path | None = None
    evidence: CollectImplementationEvidenceOutput | None = None
    prepared: PrepareReviewInputOutput | None = None
    re_review: ReviewRetryOutput | None = None
    failures: tuple[CycleFailure, ...] = ()
