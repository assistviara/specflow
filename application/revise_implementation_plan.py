from datetime import datetime
from uuid import uuid4

from application.current_state_repository import load_current_state
from application.dto import (
    ReviseImplementationPlanInput,
    ReviseImplementationPlanOutput,
)
from application.plan_revision_output_parser import (
    PlanRevisionOutputParseError,
    parse_plan_revision_output,
)
from application.state_transition import transition_state
from core.ai.prompt_adapter import PromptAdapter


class ReviseImplementationPlanUseCase:
    def __init__(
        self,
        plan_prompt_generator,
        ai_service,
    ) -> None:
        self._plan_prompt_generator = plan_prompt_generator
        self._ai_service = ai_service

    def execute(
        self,
        input_dto: ReviseImplementationPlanInput,
    ):
        current_state = load_current_state(
            input_dto.state_file
        )

        transition_state(
            input_dto.state_file,
            input_dto.state_history_dir,
            {
                "transition_id": str(uuid4()),
                "from_state": current_state["status"],
                "to_state": "plan_generating",
                "occurred_at": datetime.now().astimezone().isoformat(),
                "reason": "Implementation Plan revision started",
            },
        )

        prompt_result = (
            self._plan_prompt_generator.generate_revision(
                current_implementation_plan_path=(
                    input_dto.current_implementation_plan_path
                ),
                revision_request=input_dto.revision_request,
                specification_path=input_dto.specification_path,
                related_information=input_dto.related_information,
                template_path=input_dto.revision_template_path,
            )
        )

        ai_request = PromptAdapter.to_ai_request(
            prompt_result
        )

        ai_response = self._ai_service.run(ai_request)

        if not ai_response.success:
            return ReviseImplementationPlanOutput(
                success=False,
                revised_implementation_plan_draft=None,
                previous_implementation_plan_path=(
                    input_dto.current_implementation_plan_path
                ),
                specification_path=input_dto.specification_path,
                changes=None,
                previous_version_correspondence=None,
                error_message=ai_response.error_message,
            )

        try:
            parsed_output = parse_plan_revision_output(
                ai_response.content
            )
        except PlanRevisionOutputParseError as exc:
            return ReviseImplementationPlanOutput(
                success=False,
                revised_implementation_plan_draft=None,
                previous_implementation_plan_path=(
                    input_dto.current_implementation_plan_path
                ),
                specification_path=input_dto.specification_path,
                changes=None,
                previous_version_correspondence=None,
                error_message=str(exc),
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
                "reason": "Revised Implementation Plan Draft generated",
            },
        )

        return ReviseImplementationPlanOutput(
            success=True,
            revised_implementation_plan_draft=(
                parsed_output.revised_implementation_plan_draft
            ),
            previous_implementation_plan_path=(
                input_dto.current_implementation_plan_path
            ),
            specification_path=input_dto.specification_path,
            changes=parsed_output.changes,
            previous_version_correspondence=(
                parsed_output.previous_version_correspondence
            ),
            error_message=None,
        )