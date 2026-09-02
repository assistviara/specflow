from dataclasses import dataclass
from pathlib import Path
from typing import Any


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
    revision_request: str | None
    cancelled: bool