from datetime import datetime
from uuid import uuid4
from pathlib import Path

from application.current_state_repository import load_current_state
from application.dto import (
    GenerateImplementationPlanInput,
    GenerateImplementationPlanOutput,
)
from application.state_transition import transition_state
from core.approval_validation import validate_approval
from core.ai.prompt_adapter import PromptAdapter


class GenerateImplementationPlanUseCase:
    def __init__(
        self,
        plan_prompt_generator,
        ai_service,
        repository_validator=None,
    ) -> None:
        self._plan_prompt_generator = plan_prompt_generator
        self._ai_service = ai_service
        self._repository_validator = repository_validator

    def execute(
        self,
        input_dto: GenerateImplementationPlanInput,
    ):
        is_valid = validate_approval(
            input_dto.specification_approval,
            str(input_dto.specification_path),
            "specification",
        )

        if not is_valid:
            return None

        if self._repository_validator is not None:
            try:
                target = input_dto.project_metadata.get('target_path')
                if not isinstance(target, str) or not target.strip():
                    raise ValueError('target_path must be a nonempty string')
                path = Path(target)
                if not path.is_absolute() or not path.is_dir():
                    raise ValueError('target_path must be an existing absolute directory')
                self._repository_validator(target)
            except Exception:
                return GenerateImplementationPlanOutput(
                    success=False, implementation_plan_draft=None,
                    specification_path=input_dto.specification_path,
                    error_message='Plan target_path Repository validation failed; STOP.',
                )

        current_state = load_current_state(
            input_dto.state_file
        )

        # Workflow entry may already have persisted this transition.
        if current_state["status"] != "plan_generating":
            transition_state(
                input_dto.state_file,
                input_dto.state_history_dir,
                {
                    "transition_id": str(uuid4()),
                    "from_state": current_state["status"],
                    "to_state": "plan_generating",
                    "occurred_at": datetime.now().astimezone().isoformat(),
                    "reason": "Implementation Plan generation started",
                },
            )

        prompt_result = self._plan_prompt_generator.generate(
            constitution_path=input_dto.constitution_path,
            principles_path=input_dto.principles_path,
            specification_path=input_dto.specification_path,
            decisions_path=input_dto.decisions_path,
            implementation_plan_template_path=(
                input_dto.implementation_plan_template_path
            ),
            project_metadata=input_dto.project_metadata,
            template_path=input_dto.template_path,
        )

        ai_request = PromptAdapter.to_ai_request(prompt_result)

        ai_response = self._ai_service.run(ai_request)

        if not ai_response.success:
            return GenerateImplementationPlanOutput(
                success=False,
                implementation_plan_draft=None,
                specification_path=input_dto.specification_path,
                error_message=ai_response.error_message,
            )

        current_state = load_current_state(
            input_dto.state_file
        )

        transition_state(
            input_dto.state_file,
            input_dto.state_history_dir,
            {
                "transition_id": str(uuid4()),
                "from_state": current_state["status"],
                "to_state": "plan_approval_pending",
                "occurred_at": datetime.now().astimezone().isoformat(),
                "reason": "Implementation Plan Draft generated",
            },
        )

        return GenerateImplementationPlanOutput(
            success=True,
            implementation_plan_draft=ai_response.content,
            specification_path=input_dto.specification_path,
            error_message=None,
        )
