from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from application.dto import (
    ExecuteImplementationInput,
    ExecuteImplementationOutput,
)


def test_execute_implementation_input_is_frozen_dataclass() -> None:
    dto = ExecuteImplementationInput(
        specification_path=Path("spec.md"),
        specification_approval_id="spec-approval-1",
        implementation_plan_path=Path("plan.md"),
        implementation_plan_approval_id="plan-approval-1",
        codex_prompt="implement this",
        codex_prompt_specification_path=Path("spec.md"),
        codex_prompt_implementation_plan_path=Path("plan.md"),
        implementation_branch="developer",
        base_commit="abc123",
        working_directory=Path("."),
        state_file=Path("state.json"),
        state_history_dir=Path("state_history"),
    )

    with pytest.raises(FrozenInstanceError):
        dto.base_commit = "changed"


def test_execute_implementation_output_is_frozen_dataclass() -> None:
    dto = ExecuteImplementationOutput(
        success=False,
        implementation_result=None,
        specification_path=Path("spec.md"),
        implementation_plan_path=Path("plan.md"),
        implementation_branch="developer",
        base_commit="abc123",
        specification_approval_validation_result=None,
        implementation_plan_approval_validation_result=None,
        current_state="implementation_ready",
        technical_retry_required=False,
        critical_change_required=False,
        stop_reason=None,
        error_message=None,
    )

    with pytest.raises(FrozenInstanceError):
        dto.success = True
