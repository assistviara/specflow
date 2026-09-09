from pathlib import Path

from application.dto import GenerateCodexPromptInput


def test_generate_codex_prompt_input_holds_required_values():
    input_dto = GenerateCodexPromptInput(
        specification_path=Path("specification.md"),
        specification_approval_id="spec-approval-001",
        implementation_plan_path=Path("implementation_plan.md"),
        implementation_plan_approval_id="plan-approval-001",
        implementation_target_path=Path("application"),
        tdd_rules="Use TDD for behavior changes.",
        completion_conditions="Required tests pass.",
        stop_conditions="Stop when scope expansion is required.",
        execution_result_reporting_requirements=(
            "Report changed files, commands, and test results."
        ),
        template_path=Path("implement_prompt_template.md"),
        state_file=Path("state.json"),
        state_history_dir=Path("state_history"),
    )

    assert input_dto.specification_approval_id == "spec-approval-001"
    assert input_dto.implementation_plan_approval_id == (
        "plan-approval-001"
    )


def test_generate_codex_prompt_output_holds_result_values():
    from application.dto import GenerateCodexPromptOutput
    from core.approval_validation import ApprovalValidationResult

    specification_validation = ApprovalValidationResult(
        is_valid=True,
        approval_id="spec-approval-001",
        artifact_type="specification",
        validation_errors=[],
        validation_warnings=[],
    )
    plan_validation = ApprovalValidationResult(
        is_valid=True,
        approval_id="plan-approval-001",
        artifact_type="implementation_plan",
        validation_errors=[],
        validation_warnings=[],
    )

    output_dto = GenerateCodexPromptOutput(
        success=True,
        codex_prompt="Generated Codex Prompt",
        specification_path=Path("specification.md"),
        implementation_plan_path=Path("implementation_plan.md"),
        specification_approval_validation_result=specification_validation,
        implementation_plan_approval_validation_result=plan_validation,
        prompt_usable=True,
        current_state="implementation_ready",
    )

    assert output_dto.success is True
    assert output_dto.codex_prompt == "Generated Codex Prompt"
    assert (
        output_dto.specification_approval_validation_result
        is specification_validation
    )
    assert (
        output_dto.implementation_plan_approval_validation_result
        is plan_validation
    )
    assert output_dto.prompt_usable is True
    assert output_dto.current_state == "implementation_ready"
    assert output_dto.stop_reason is None
    assert output_dto.error_message is None
