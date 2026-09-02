from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from application.dto import (
    RequestPlanApprovalInput,
    RequestPlanApprovalOutput,
)


def test_request_plan_approval_input_keeps_boundary_data():
    input_dto = RequestPlanApprovalInput(
        implementation_plan_path=Path("plan.md"),
        human_decision="approved",
        comment="Human approved the plan.",
        approval_id="plan-approval-001",
        approved_at="2026-09-02T12:00:00+09:00",
        state_file=Path("state.json"),
        state_history_dir=Path("state_history"),
    )

    assert input_dto.implementation_plan_path == Path("plan.md")
    assert input_dto.human_decision == "approved"
    assert input_dto.comment == "Human approved the plan."
    assert input_dto.approval_id == "plan-approval-001"
    assert input_dto.approved_at == "2026-09-02T12:00:00+09:00"
    assert input_dto.state_file == Path("state.json")
    assert input_dto.state_history_dir == Path("state_history")


def test_request_plan_approval_output_keeps_result_data():
    record = {"approval_id": "plan-approval-001"}

    output_dto = RequestPlanApprovalOutput(
        decision="approved",
        approval_record=record,
        approval_valid=True,
        revision_request=None,
        cancelled=False,
    )

    assert output_dto.decision == "approved"
    assert output_dto.approval_record == record
    assert output_dto.approval_valid is True
    assert output_dto.revision_request is None
    assert output_dto.cancelled is False


def test_request_plan_approval_dtos_are_frozen():
    input_dto = RequestPlanApprovalInput(
        implementation_plan_path=Path("plan.md"),
        human_decision="approved",
        comment="",
        approval_id="plan-approval-001",
        approved_at="2026-09-02T12:00:00+09:00",
        state_file=Path("state.json"),
        state_history_dir=Path("state_history"),
    )

    with pytest.raises(FrozenInstanceError):
        input_dto.human_decision = "cancelled"
