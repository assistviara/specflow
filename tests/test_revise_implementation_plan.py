import json
from pathlib import Path
from unittest.mock import Mock

from application.dto import ReviseImplementationPlanInput
from application.revise_implementation_plan import (
    ReviseImplementationPlanUseCase,
)


def test_execute_transitions_to_plan_generating(
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "state.json"
    state_history_dir = tmp_path / "state_history"

    state_file.write_text(
        json.dumps(
            {
                "status": "plan_revision_requested",
            }
        ),
        encoding="utf-8",
    )

    plan_prompt_generator = Mock()
    prompt_result = Mock()
    prompt_result.is_ready = True
    prompt_result.content = "revision prompt"
    plan_prompt_generator.generate_revision.return_value = (
        prompt_result
    )

    ai_service = Mock()
    ai_response = Mock()
    ai_response.success = False
    ai_response.error_message = "AI execution failed"
    ai_service.run.return_value = ai_response

    use_case = ReviseImplementationPlanUseCase(
        plan_prompt_generator=plan_prompt_generator,
        ai_service=ai_service,
    )

    input_dto = ReviseImplementationPlanInput(
        current_implementation_plan_path=(
            tmp_path / "current_plan.md"
        ),
        revision_request="Revise the implementation scope.",
        specification_path=tmp_path / "specification.md",
        related_information=None,
        revision_template_path=(
            tmp_path / "plan_revision_prompt_template.md"
        ),
        state_file=state_file,
        state_history_dir=state_history_dir,
    )

    use_case.execute(input_dto)

    state = json.loads(
        state_file.read_text(encoding="utf-8")
    )

    assert state["status"] == "plan_generating"


def test_execute_generates_revision_prompt(
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "state.json"
    state_history_dir = tmp_path / "state_history"

    state_file.write_text(
        json.dumps(
            {
                "status": "plan_revision_requested",
            }
        ),
        encoding="utf-8",
    )

    plan_prompt_generator = Mock()

    prompt_result = Mock()
    prompt_result.is_ready = True
    prompt_result.content = "revision prompt"
    plan_prompt_generator.generate_revision.return_value = (
        prompt_result
    )

    ai_service = Mock()
    ai_response = Mock()
    ai_response.success = False
    ai_response.error_message = "AI execution failed"
    ai_service.run.return_value = ai_response

    use_case = ReviseImplementationPlanUseCase(
        plan_prompt_generator=plan_prompt_generator,
        ai_service=ai_service,
    )

    input_dto = ReviseImplementationPlanInput(
        current_implementation_plan_path=(
            tmp_path / "current_plan.md"
        ),
        revision_request="Revise the implementation scope.",
        specification_path=tmp_path / "specification.md",
        related_information="Related information.",
        revision_template_path=(
            tmp_path / "plan_revision_prompt_template.md"
        ),
        state_file=state_file,
        state_history_dir=state_history_dir,
    )

    use_case.execute(input_dto)

    plan_prompt_generator.generate_revision.assert_called_once_with(
        current_implementation_plan_path=(
            input_dto.current_implementation_plan_path
        ),
        revision_request=input_dto.revision_request,
        specification_path=input_dto.specification_path,
        related_information=input_dto.related_information,
        template_path=input_dto.revision_template_path,
    )


def test_execute_sends_revision_prompt_to_ai_service(
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "state.json"
    state_history_dir = tmp_path / "state_history"

    state_file.write_text(
        json.dumps(
            {
                "status": "plan_revision_requested",
            }
        ),
        encoding="utf-8",
    )

    plan_prompt_generator = Mock()
    prompt_result = Mock()
    prompt_result.is_ready = True
    prompt_result.content = "revision prompt"
    plan_prompt_generator.generate_revision.return_value = (
        prompt_result
    )

    ai_service = Mock()
    ai_response = Mock()
    ai_response.success = False
    ai_response.error_message = "AI execution failed"
    ai_service.run.return_value = ai_response

    use_case = ReviseImplementationPlanUseCase(
        plan_prompt_generator=plan_prompt_generator,
        ai_service=ai_service,
    )

    input_dto = ReviseImplementationPlanInput(
        current_implementation_plan_path=(
            tmp_path / "current_plan.md"
        ),
        revision_request="Revise the implementation scope.",
        specification_path=tmp_path / "specification.md",
        related_information="Related information.",
        revision_template_path=(
            tmp_path / "plan_revision_prompt_template.md"
        ),
        state_file=state_file,
        state_history_dir=state_history_dir,
    )

    use_case.execute(input_dto)

    ai_service.run.assert_called_once()

    ai_request = ai_service.run.call_args.args[0]

    assert ai_request.prompt == "revision prompt"


def test_execute_returns_failure_when_ai_fails(
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "state.json"
    state_history_dir = tmp_path / "state_history"

    state_file.write_text(
        json.dumps(
            {
                "status": "plan_revision_requested",
            }
        ),
        encoding="utf-8",
    )

    plan_prompt_generator = Mock()
    prompt_result = Mock()
    prompt_result.is_ready = True
    prompt_result.content = "revision prompt"
    plan_prompt_generator.generate_revision.return_value = (
        prompt_result
    )

    ai_service = Mock()
    ai_response = Mock()
    ai_response.success = False
    ai_response.error_message = "AI execution failed"
    ai_service.run.return_value = ai_response

    use_case = ReviseImplementationPlanUseCase(
        plan_prompt_generator=plan_prompt_generator,
        ai_service=ai_service,
    )

    input_dto = ReviseImplementationPlanInput(
        current_implementation_plan_path=(
            tmp_path / "current_plan.md"
        ),
        revision_request="Revise the implementation scope.",
        specification_path=tmp_path / "specification.md",
        related_information=None,
        revision_template_path=(
            tmp_path / "plan_revision_prompt_template.md"
        ),
        state_file=state_file,
        state_history_dir=state_history_dir,
    )

    output = use_case.execute(input_dto)

    assert output.success is False
    assert output.revised_implementation_plan_draft is None
    assert (
        output.previous_implementation_plan_path
        == input_dto.current_implementation_plan_path
    )
    assert output.specification_path == input_dto.specification_path
    assert output.changes is None
    assert output.previous_version_correspondence is None
    assert output.error_message == "AI execution failed"

    state = json.loads(
        state_file.read_text(encoding="utf-8")
    )

    assert state["status"] == "plan_generating"


def test_execute_parses_successful_ai_response(
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "state.json"
    state_history_dir = tmp_path / "state_history"

    state_file.write_text(
        json.dumps(
            {
                "status": "plan_revision_requested",
            }
        ),
        encoding="utf-8",
    )

    plan_prompt_generator = Mock()
    prompt_result = Mock()
    prompt_result.is_ready = True
    prompt_result.content = "revision prompt"
    plan_prompt_generator.generate_revision.return_value = (
        prompt_result
    )

    ai_service = Mock()
    ai_response = Mock()
    ai_response.success = True
    ai_response.content = """
### REVISED_IMPLEMENTATION_PLAN

Revised implementation plan.

### CHANGES

Changed the implementation scope.

### PREVIOUS_VERSION_CORRESPONDENCE

Section 2 corresponds to revised Section 2.
"""
    ai_response.error_message = None
    ai_service.run.return_value = ai_response

    use_case = ReviseImplementationPlanUseCase(
        plan_prompt_generator=plan_prompt_generator,
        ai_service=ai_service,
    )

    input_dto = ReviseImplementationPlanInput(
        current_implementation_plan_path=(
            tmp_path / "current_plan.md"
        ),
        revision_request="Revise the implementation scope.",
        specification_path=tmp_path / "specification.md",
        related_information=None,
        revision_template_path=(
            tmp_path / "plan_revision_prompt_template.md"
        ),
        state_file=state_file,
        state_history_dir=state_history_dir,
    )

    output = use_case.execute(input_dto)

    assert (
        output.revised_implementation_plan_draft
        == "Revised implementation plan."
    )
    assert (
        output.changes
        == "Changed the implementation scope."
    )
    assert (
        output.previous_version_correspondence
        == "Section 2 corresponds to revised Section 2."
    )


def test_execute_transitions_to_plan_approval_pending_after_success(
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "state.json"
    state_history_dir = tmp_path / "state_history"

    state_file.write_text(
        json.dumps(
            {
                "status": "plan_revision_requested",
            }
        ),
        encoding="utf-8",
    )

    plan_prompt_generator = Mock()
    prompt_result = Mock()
    prompt_result.is_ready = True
    prompt_result.content = "revision prompt"
    plan_prompt_generator.generate_revision.return_value = (
        prompt_result
    )

    ai_service = Mock()
    ai_response = Mock()
    ai_response.success = True
    ai_response.content = """
### REVISED_IMPLEMENTATION_PLAN

Revised implementation plan.

### CHANGES

Changed the implementation scope.

### PREVIOUS_VERSION_CORRESPONDENCE

Section 2 corresponds to revised Section 2.
"""
    ai_response.error_message = None
    ai_service.run.return_value = ai_response

    use_case = ReviseImplementationPlanUseCase(
        plan_prompt_generator=plan_prompt_generator,
        ai_service=ai_service,
    )

    input_dto = ReviseImplementationPlanInput(
        current_implementation_plan_path=(
            tmp_path / "current_plan.md"
        ),
        revision_request="Revise the implementation scope.",
        specification_path=tmp_path / "specification.md",
        related_information=None,
        revision_template_path=(
            tmp_path / "plan_revision_prompt_template.md"
        ),
        state_file=state_file,
        state_history_dir=state_history_dir,
    )

    output = use_case.execute(input_dto)

    assert output.success is True

    state = json.loads(
        state_file.read_text(encoding="utf-8")
    )

    assert state["status"] == "plan_approval_pending"


def test_execute_returns_failure_when_ai_output_cannot_be_parsed(
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "state.json"
    state_history_dir = tmp_path / "state_history"

    state_file.write_text(
        json.dumps(
            {
                "status": "plan_revision_requested",
            }
        ),
        encoding="utf-8",
    )

    plan_prompt_generator = Mock()
    prompt_result = Mock()
    prompt_result.is_ready = True
    prompt_result.content = "revision prompt"
    plan_prompt_generator.generate_revision.return_value = (
        prompt_result
    )

    ai_service = Mock()
    ai_response = Mock()
    ai_response.success = True
    ai_response.content = "Invalid AI output"
    ai_response.error_message = None
    ai_service.run.return_value = ai_response

    use_case = ReviseImplementationPlanUseCase(
        plan_prompt_generator=plan_prompt_generator,
        ai_service=ai_service,
    )

    input_dto = ReviseImplementationPlanInput(
        current_implementation_plan_path=(
            tmp_path / "current_plan.md"
        ),
        revision_request="Revise the implementation scope.",
        specification_path=tmp_path / "specification.md",
        related_information=None,
        revision_template_path=(
            tmp_path / "plan_revision_prompt_template.md"
        ),
        state_file=state_file,
        state_history_dir=state_history_dir,
    )

    output = use_case.execute(input_dto)

    assert output.success is False
    assert output.revised_implementation_plan_draft is None
    assert output.changes is None
    assert output.previous_version_correspondence is None
    assert output.error_message == "required section is missing"

    state = json.loads(
        state_file.read_text(encoding="utf-8")
    )

    assert state["status"] == "plan_generating"