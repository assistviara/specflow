import hashlib

from core.approval_record_service import build_approval_record_from_artifact


def test_build_approval_record_from_artifact_calculates_sha256_and_keeps_human_decision(
    tmp_path,
):
    artifact_path = tmp_path / "implementation_plan.md"
    artifact_path.write_text("approved plan content", encoding="utf-8")

    record = build_approval_record_from_artifact(
        approval_id="plan-approval-001",
        artifact_type="implementation_plan",
        artifact_path=str(artifact_path),
        decision="approved",
        approved_at="2026-09-02T12:00:00+09:00",
        comment="Human approved the plan.",
    )

    expected_hash = hashlib.sha256(
        artifact_path.read_bytes()
    ).hexdigest()

    assert record == {
        "approval_id": "plan-approval-001",
        "artifact_type": "implementation_plan",
        "artifact_path": str(artifact_path),
        "artifact_hash": expected_hash,
        "decision": "approved",
        "approved_at": "2026-09-02T12:00:00+09:00",
        "comment": "Human approved the plan.",
    }
