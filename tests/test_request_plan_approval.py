from pathlib import Path

from application.dto import RequestPlanApprovalInput
from application.request_plan_approval import RequestPlanApprovalUseCase
from core.approval_record_repository import ApprovalRecordRepository


class FakeApprovalRecordRepository(ApprovalRecordRepository):
    def __init__(self):
        self.saved_record = None

    def save(self, record: dict) -> None:
        self.saved_record = record

    def get(self, approval_id: str) -> dict:
        if self.saved_record is None:
            return None

        if self.saved_record["approval_id"] == approval_id:
            return self.saved_record

        return None


def test_request_plan_approval_saves_human_approval_record(tmp_path):
    implementation_plan_path = tmp_path / "implementation_plan.md"
    implementation_plan_path.write_text(
        "approved implementation plan",
        encoding="utf-8",
    )

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"status": "plan_approval_pending"}',
        encoding="utf-8",
    )

    state_history_dir = tmp_path / "state_history"

    repository = FakeApprovalRecordRepository()

    use_case = RequestPlanApprovalUseCase(
        approval_repository=repository,
    )

    input_dto = RequestPlanApprovalInput(
        implementation_plan_path=implementation_plan_path,
        human_decision="approved",
        comment="Human approved the plan.",
        approval_id="plan-approval-001",
        approved_at="2026-09-02T12:00:00+09:00",
        state_file=state_file,
        state_history_dir=state_history_dir,
    )

    use_case.execute(input_dto)

    assert repository.saved_record is not None
    assert repository.saved_record["approval_id"] == "plan-approval-001"
    assert repository.saved_record["artifact_type"] == "implementation_plan"
    assert repository.saved_record["artifact_path"] == str(
        implementation_plan_path
    )
    assert repository.saved_record["decision"] == "approved"
    assert repository.saved_record["comment"] == "Human approved the plan."

def test_request_plan_approval_moves_to_plan_approved_when_approval_is_valid(
    tmp_path,
):
    implementation_plan_path = tmp_path / "implementation_plan.md"
    implementation_plan_path.write_text(
        "approved implementation plan",
        encoding="utf-8",
    )

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"status": "plan_approval_pending"}',
        encoding="utf-8",
    )

    state_history_dir = tmp_path / "state_history"

    repository = FakeApprovalRecordRepository()

    use_case = RequestPlanApprovalUseCase(
        approval_repository=repository,
    )

    input_dto = RequestPlanApprovalInput(
        implementation_plan_path=implementation_plan_path,
        human_decision="approved",
        comment="Human approved the plan.",
        approval_id="plan-approval-001",
        approved_at="2026-09-02T12:00:00+09:00",
        state_file=state_file,
        state_history_dir=state_history_dir,
    )

    output = use_case.execute(input_dto)

    assert output.approval_valid is True
    assert output.decision == "approved"

    current_state = state_file.read_text(encoding="utf-8")
    assert '"status": "plan_approved"' in current_state
