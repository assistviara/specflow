from pathlib import Path

from application.dto import (
    ReviseImplementationPlanInput,
    ReviseImplementationPlanOutput,
)


def test_revise_implementation_plan_input_keeps_data():
    input_dto = ReviseImplementationPlanInput(
        current_implementation_plan_path=Path("current_plan.md"),
        revision_request="Please revise the implementation scope.",
        specification_path=Path("specification.md"),
        related_information="Related implementation information.",
        revision_template_path=Path("plan_revision_prompt_template.md"),
        state_file=Path("state.json"),
        state_history_dir=Path("state_history"),
    )

    assert (
        input_dto.current_implementation_plan_path
        == Path("current_plan.md")
    )
    assert (
        input_dto.revision_request
        == "Please revise the implementation scope."
    )
    assert (
        input_dto.revision_template_path
        == Path("plan_revision_prompt_template.md")
    )
    assert input_dto.specification_path == Path("specification.md")
    assert (
        input_dto.related_information
        == "Related implementation information."
    )
    assert input_dto.state_file == Path("state.json")
    assert input_dto.state_history_dir == Path("state_history")


def test_revise_implementation_plan_output_keeps_data():
    output_dto = ReviseImplementationPlanOutput(
        success=True,
        revised_implementation_plan_draft="revised plan",
        previous_implementation_plan_path=Path("current_plan.md"),
        specification_path=Path("specification.md"),
        changes="Changed implementation scope.",
        error_message=None,
        previous_version_correspondence=(
            "Section 2 corresponds to the revised implementation scope."
        ),
    )

    assert output_dto.success is True
    assert (
        output_dto.revised_implementation_plan_draft
        == "revised plan"
    )
    assert (
        output_dto.previous_implementation_plan_path
        == Path("current_plan.md")
    )
    assert output_dto.specification_path == Path("specification.md")
    assert output_dto.changes == "Changed implementation scope."
    assert output_dto.error_message is None
    assert output_dto.previous_version_correspondence == (
        "Section 2 corresponds to the revised implementation scope."
)