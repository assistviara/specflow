from dataclasses import dataclass
from pathlib import Path
from typing import Any

from application.implementation_evidence import EvidenceScope
from uuid import UUID

from core.approval_validation import ApprovalValidationResult


@dataclass(frozen=True)
class InputDTO:
    pass


@dataclass(frozen=True)
class OutputDTO:
    pass


@dataclass(frozen=True)
class GenerateImplementationPlanInput:
    constitution_path: Path
    principles_path: Path
    specification_path: Path
    specification_approval: dict
    decisions_path: Path
    implementation_plan_template_path: Path
    project_metadata: dict[str, Any]
    template_path: Path
    state_file: Path
    state_history_dir: Path


@dataclass(frozen=True)
class GenerateImplementationPlanOutput:
    success: bool
    implementation_plan_draft: str | None
    specification_path: Path
    error_message: str | None = None

@dataclass(frozen=True)
class RequestPlanApprovalInput:
    implementation_plan_path: Path
    human_decision: str
    comment: str
    approval_id: str
    approved_at: str
    state_file: Path
    state_history_dir: Path


@dataclass(frozen=True)
class RequestPlanApprovalOutput:
    decision: str
    approval_record: dict
    approval_valid: bool
    approval_validation_result: ApprovalValidationResult
    revision_request: str | None
    cancelled: bool

@dataclass(frozen=True)
class ReviseImplementationPlanInput:
    current_implementation_plan_path: Path
    revision_request: str
    specification_path: Path
    related_information: str | None
    revision_template_path: Path
    state_file: Path
    state_history_dir: Path

@dataclass(frozen=True)
class ReviseImplementationPlanOutput:
    success: bool
    revised_implementation_plan_draft: str | None
    previous_implementation_plan_path: Path
    specification_path: Path
    changes: str | None
    previous_version_correspondence: str | None
    error_message: str | None = None
    

@dataclass(frozen=True)
class GenerateCodexPromptInput:
    specification_path: Path
    specification_approval_id: str
    implementation_plan_path: Path
    implementation_plan_approval_id: str
    implementation_target_path: Path
    tdd_rules: str
    completion_conditions: str
    stop_conditions: str
    execution_result_reporting_requirements: str
    template_path: Path
    state_file: Path
    state_history_dir: Path


@dataclass(frozen=True)
class GenerateCodexPromptOutput:
    success: bool
    codex_prompt: str | None
    specification_path: Path
    implementation_plan_path: Path
    specification_approval_validation_result: ApprovalValidationResult
    implementation_plan_approval_validation_result: ApprovalValidationResult
    prompt_usable: bool
    current_state: str
    stop_reason: str | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class ExecuteImplementationInput:
    specification_path: Path
    specification_approval_id: str
    implementation_plan_path: Path
    implementation_plan_approval_id: str
    codex_prompt: str
    codex_prompt_specification_path: Path
    codex_prompt_implementation_plan_path: Path
    implementation_branch: str
    base_commit: str
    working_directory: Path
    state_file: Path
    state_history_dir: Path


@dataclass(frozen=True)
class ExecuteImplementationOutput:
    success: bool
    implementation_result: Any | None
    specification_path: Path
    implementation_plan_path: Path
    implementation_branch: str
    base_commit: str
    specification_approval_validation_result: ApprovalValidationResult
    implementation_plan_approval_validation_result: ApprovalValidationResult
    current_state: str
    technical_retry_required: bool
    critical_change_required: bool
    stop_reason: str | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class CollectImplementationEvidenceInput:
    implementation_id: UUID
    implementation_kind: str
    previous_evidence_id: UUID | None
    specification_path: Path
    specification_approval_id: str
    implementation_plan_path: Path
    implementation_plan_approval_id: str
    codex_prompt_path: Path
    codex_prompt: str
    implementation_branch: str
    base_commit: str
    implementation_result: Any | None
    approved_scope: "EvidenceScope | None"


@dataclass(frozen=True)
class CollectImplementationEvidenceOutput:
    success: bool
    evidence_id: UUID
    implementation_id: UUID
    implementation_evidence: Any | None
    evidence_path: Path
    git_diff_path: Path
    status: str
    missing_evidence: tuple[str, ...]
    inconsistencies: tuple[str, ...]
    human_approval_required: tuple[str, ...]
    error_message: str | None = None
