from datetime import datetime
from uuid import uuid4

from application.current_state_repository import load_current_state
from application.dto import (
    RequestPlanApprovalInput,
    RequestPlanApprovalOutput,
)
from application.state_transition import transition_state
from core.approval_record_service import (
    build_approval_record_from_artifact,
)
from core.approval_validation import validate_approval


class RequestPlanApprovalUseCase:
    def __init__(
        self,
        approval_repository,
    ) -> None:
        self._approval_repository = approval_repository

    def execute(
        self,
        input_dto: RequestPlanApprovalInput,
    ):
        approval_record = build_approval_record_from_artifact(
            approval_id=input_dto.approval_id,
            artifact_type="implementation_plan",
            artifact_path=str(input_dto.implementation_plan_path),
            decision=input_dto.human_decision,
            approved_at=input_dto.approved_at,
            comment=input_dto.comment,
        )

        self._approval_repository.save(approval_record)

        approval_valid = validate_approval(
            approval_record,
            str(input_dto.implementation_plan_path),
            "implementation_plan",
        )

        if approval_valid:
            current_state = load_current_state(
                input_dto.state_file
            )

            transition_state(
                input_dto.state_file,
                input_dto.state_history_dir,
                {
                    "transition_id": str(uuid4()),
                    "from_state": current_state["status"],
                    "to_state": "plan_approved",
                    "occurred_at": datetime.now().astimezone().isoformat(),
                    "reason": "Implementation Plan approved",
                },
            )

        return RequestPlanApprovalOutput(
            decision=input_dto.human_decision,
            approval_record=approval_record,
            approval_valid=approval_valid,
            revision_request=None,
            cancelled=False,
        )