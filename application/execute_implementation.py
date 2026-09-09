from datetime import datetime
from uuid import uuid4

from application.current_state_repository import load_current_state
from application.dto import (
    ExecuteImplementationInput,
    ExecuteImplementationOutput,
)
from application.implementation_result_parser import (
    ImplementationResultParser,
)
from application.state_transition import transition_state
from core.approval_validation import validate_approval_result


class ExecuteImplementationUseCase:
    def __init__(
        self,
        approval_repository,
        implementation_adapter,
    ) -> None:
        self._approval_repository = approval_repository
        self._implementation_adapter = implementation_adapter

    def execute(
        self,
        input_dto: ExecuteImplementationInput,
    ) -> ExecuteImplementationOutput:
        specification_record = self._approval_repository.get(
            input_dto.specification_approval_id
        )
        implementation_plan_record = self._approval_repository.get(
            input_dto.implementation_plan_approval_id
        )

        specification_validation = validate_approval_result(
            specification_record,
            str(input_dto.specification_path),
            "specification",
        )
        implementation_plan_validation = validate_approval_result(
            implementation_plan_record,
            str(input_dto.implementation_plan_path),
            "implementation_plan",
        )

        current_state = load_current_state(
            input_dto.state_file
        )["status"]

        if (
            not specification_validation.is_valid
            or not implementation_plan_validation.is_valid
        ):
            return ExecuteImplementationOutput(
                success=False,
                implementation_result=None,
                specification_path=input_dto.specification_path,
                implementation_plan_path=input_dto.implementation_plan_path,
                implementation_branch=input_dto.implementation_branch,
                base_commit=input_dto.base_commit,
                specification_approval_validation_result=(
                    specification_validation
                ),
                implementation_plan_approval_validation_result=(
                    implementation_plan_validation
                ),
                current_state=current_state,
                technical_retry_required=False,
                critical_change_required=False,
                stop_reason="Approval validation failed.",
            )

        if (
            input_dto.codex_prompt_specification_path
            != input_dto.specification_path
            or input_dto.codex_prompt_implementation_plan_path
            != input_dto.implementation_plan_path
        ):
            return ExecuteImplementationOutput(
                success=False,
                implementation_result=None,
                specification_path=input_dto.specification_path,
                implementation_plan_path=input_dto.implementation_plan_path,
                implementation_branch=input_dto.implementation_branch,
                base_commit=input_dto.base_commit,
                specification_approval_validation_result=(
                    specification_validation
                ),
                implementation_plan_approval_validation_result=(
                    implementation_plan_validation
                ),
                current_state=current_state,
                technical_retry_required=False,
                critical_change_required=False,
                stop_reason=(
                    "Codex Prompt correspondence validation failed."
                ),
            )

        transition_state(
            input_dto.state_file,
            input_dto.state_history_dir,
            {
                "transition_id": str(uuid4()),
                "from_state": current_state,
                "to_state": "implementing",
                "occurred_at": datetime.now().astimezone().isoformat(),
                "reason": "Implementation execution started",
            },
        )

        raw_result = self._implementation_adapter.run(
            prompt=input_dto.codex_prompt,
            working_directory=input_dto.working_directory,
        )

        implementation_result = ImplementationResultParser.parse(
            raw_result
        )

        current_state = load_current_state(
            input_dto.state_file
        )["status"]

        if implementation_result.test_execution_status == "ERROR":
            technical_retry_allowed = (
                implementation_result.technical_retry_safe is True
                and implementation_result.technical_retry_operation
                is not None
                and implementation_result.changed_files.strip() == "NONE"
            )

            if technical_retry_allowed:
                raw_result = self._implementation_adapter.run(
                    prompt=input_dto.codex_prompt,
                    working_directory=input_dto.working_directory,
                )

                implementation_result = (
                    ImplementationResultParser.parse(raw_result)
                )

                current_state = load_current_state(
                    input_dto.state_file
                )["status"]

            if implementation_result.test_execution_status == "ERROR":
                transition_state(
                    input_dto.state_file,
                    input_dto.state_history_dir,
                    {
                        "transition_id": str(uuid4()),
                        "from_state": current_state,
                        "to_state": "implementation_failed",
                        "occurred_at": (
                            datetime.now().astimezone().isoformat()
                        ),
                        "reason": "Implementation test execution error",
                    },
                )

                return ExecuteImplementationOutput(
                    success=False,
                    implementation_result=implementation_result,
                    specification_path=input_dto.specification_path,
                    implementation_plan_path=(
                        input_dto.implementation_plan_path
                    ),
                    implementation_branch=input_dto.implementation_branch,
                    base_commit=input_dto.base_commit,
                    specification_approval_validation_result=(
                        specification_validation
                    ),
                    implementation_plan_approval_validation_result=(
                        implementation_plan_validation
                    ),
                    current_state="implementation_failed",
                    technical_retry_required=False,
                    critical_change_required=False,
                    stop_reason="Test execution error.",
                )

        transition_state(
            input_dto.state_file,
            input_dto.state_history_dir,
            {
                "transition_id": str(uuid4()),
                "from_state": current_state,
                "to_state": "implementation_completed",
                "occurred_at": datetime.now().astimezone().isoformat(),
                "reason": "Implementation execution completed",
            },
        )

        return ExecuteImplementationOutput(
            success=True,
            implementation_result=implementation_result,
            specification_path=input_dto.specification_path,
            implementation_plan_path=input_dto.implementation_plan_path,
            implementation_branch=input_dto.implementation_branch,
            base_commit=input_dto.base_commit,
            specification_approval_validation_result=(
                specification_validation
            ),
            implementation_plan_approval_validation_result=(
                implementation_plan_validation
            ),
            current_state="implementation_completed",
            technical_retry_required=False,
            critical_change_required=False,
        )
