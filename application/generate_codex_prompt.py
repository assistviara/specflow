from datetime import datetime
from uuid import uuid4

from application.current_state_repository import load_current_state
from application.dto import (
    GenerateCodexPromptInput,
    GenerateCodexPromptOutput,
)
from application.state_transition import transition_state
from application.codex_prompt_output_parser import (
    CodexPromptOutputParseError,
    parse_codex_prompt_output,
)
from core.approval_validation import validate_approval_result
from core.ai.prompt_adapter import PromptAdapter


class GenerateCodexPromptUseCase:
    def __init__(
        self,
        approval_repository,
        prompt_generator,
        ai_service,
    ) -> None:
        self._approval_repository = approval_repository
        self._prompt_generator = prompt_generator
        self._ai_service = ai_service

    def execute(
        self,
        input_dto: GenerateCodexPromptInput,
    ) -> GenerateCodexPromptOutput:
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
            return GenerateCodexPromptOutput(
                success=False,
                codex_prompt=None,
                specification_path=input_dto.specification_path,
                implementation_plan_path=(
                    input_dto.implementation_plan_path
                ),
                specification_approval_validation_result=(
                    specification_validation
                ),
                implementation_plan_approval_validation_result=(
                    implementation_plan_validation
                ),
                prompt_usable=False,
                current_state=current_state,
                stop_reason="Approval validation failed.",
            )

        transition_state(
            input_dto.state_file,
            input_dto.state_history_dir,
            {
                "transition_id": str(uuid4()),
                "from_state": current_state,
                "to_state": "implementation_prompt_generating",
                "occurred_at": datetime.now().astimezone().isoformat(),
                "reason": "Codex Implementation Prompt generation started",
            },
        )

        prompt_result = self._prompt_generator.generate(
            specification_path=input_dto.specification_path,
            implementation_plan_path=input_dto.implementation_plan_path,
            implementation_target_path=(
                input_dto.implementation_target_path
            ),
            tdd_rules=input_dto.tdd_rules,
            completion_conditions=input_dto.completion_conditions,
            stop_conditions=input_dto.stop_conditions,
            execution_result_reporting_requirements=(
                input_dto.execution_result_reporting_requirements
            ),
            template_path=input_dto.template_path,
        )

        try:
            ai_request = PromptAdapter.to_ai_request(
                prompt_result
            )
        except ValueError as exc:
            current_state = load_current_state(
                input_dto.state_file
            )["status"]

            return GenerateCodexPromptOutput(
                success=False,
                codex_prompt=None,
                specification_path=input_dto.specification_path,
                implementation_plan_path=(
                    input_dto.implementation_plan_path
                ),
                specification_approval_validation_result=(
                    specification_validation
                ),
                implementation_plan_approval_validation_result=(
                    implementation_plan_validation
                ),
                prompt_usable=False,
                current_state=current_state,
                stop_reason=str(exc),
                error_message=str(exc),
            )

        ai_response = self._ai_service.run(
            ai_request
        )

        if not ai_response.success:
            current_state = load_current_state(
                input_dto.state_file
            )["status"]

            return GenerateCodexPromptOutput(
                success=False,
                codex_prompt=None,
                specification_path=input_dto.specification_path,
                implementation_plan_path=(
                    input_dto.implementation_plan_path
                ),
                specification_approval_validation_result=(
                    specification_validation
                ),
                implementation_plan_approval_validation_result=(
                    implementation_plan_validation
                ),
                prompt_usable=False,
                current_state=current_state,
                stop_reason=ai_response.error_message,
                error_message=ai_response.error_message,
            )

        try:
            parse_codex_prompt_output(
                ai_response.content
            )
        except CodexPromptOutputParseError as exc:
            current_state = load_current_state(
                input_dto.state_file
            )["status"]

            return GenerateCodexPromptOutput(
                success=False,
                codex_prompt=None,
                specification_path=input_dto.specification_path,
                implementation_plan_path=(
                    input_dto.implementation_plan_path
                ),
                specification_approval_validation_result=(
                    specification_validation
                ),
                implementation_plan_approval_validation_result=(
                    implementation_plan_validation
                ),
                prompt_usable=False,
                current_state=current_state,
                stop_reason=str(exc),
                error_message=str(exc),
            )

        current_state = load_current_state(
            input_dto.state_file
        )["status"]

        transition_state(
            input_dto.state_file,
            input_dto.state_history_dir,
            {
                "transition_id": str(uuid4()),
                "from_state": current_state,
                "to_state": "implementation_ready",
                "occurred_at": datetime.now().astimezone().isoformat(),
                "reason": "Codex Implementation Prompt generated",
            },
        )

        return GenerateCodexPromptOutput(
            success=True,
            codex_prompt=ai_response.content,
            specification_path=input_dto.specification_path,
            implementation_plan_path=(
                input_dto.implementation_plan_path
            ),
            specification_approval_validation_result=(
                specification_validation
            ),
            implementation_plan_approval_validation_result=(
                implementation_plan_validation
            ),
            prompt_usable=True,
            current_state="implementation_ready",
        )
