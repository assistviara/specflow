from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from application.dto import (
    GenerateImplementationPlanInput,
    GenerateImplementationPlanOutput,
)


def test_generate_implementation_plan_input_is_frozen():
    dto = GenerateImplementationPlanInput(
        constitution_path=Path("constitution.md"),
        principles_path=Path("principles.md"),
        specification_path=Path("specification.md"),
        specification_approval={"approval_id": "approval-001"},
        decisions_path=Path("decisions.md"),
        implementation_plan_template_path=Path(
            "implementation_plan_template.md"
        ),
        project_metadata={"project_name": "specflow"},
        template_path=Path("plan_prompt.md"),
        state_file=Path("state.json"),
        state_history_dir=Path("state_history"),
    )

    with pytest.raises(FrozenInstanceError):
        dto.specification_path = Path("changed.md")


def test_generate_implementation_plan_output_is_frozen():
    dto = GenerateImplementationPlanOutput(
        success=True,
        implementation_plan_draft="# Implementation Plan",
        specification_path=Path("specification.md"),
    )

    with pytest.raises(FrozenInstanceError):
        dto.implementation_plan_draft = "changed"

def test_generate_implementation_plan_output_can_represent_failure(
    tmp_path: Path,
):
    specification_path = tmp_path / "specification.md"

    output = GenerateImplementationPlanOutput(
        success=False,
        implementation_plan_draft=None,
        specification_path=specification_path,
        error_message="Plan generation failed",
    )

    assert output.success is False
    assert output.implementation_plan_draft is None
    assert output.specification_path == specification_path
    assert output.error_message == "Plan generation failed"