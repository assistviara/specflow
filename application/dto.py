from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
