from core.approval_record import build_approval_record


def test_build_approval_record_keeps_human_decision_and_required_fields():
    record = build_approval_record(
        approval_id="approval-001",
        artifact_type="implementation_plan",
        artifact_path="projects/specflow/docs/drafts/application_layer_implementation_plan_v0.1.0-draft.md",
        artifact_hash="abc123",
        decision="approved",
        approved_at="2026-08-31T17:30:00+09:00",
        comment="Human approved the implementation plan.",
    )

    assert record == {
        "approval_id": "approval-001",
        "artifact_type": "implementation_plan",
        "artifact_path": "projects/specflow/docs/drafts/application_layer_implementation_plan_v0.1.0-draft.md",
        "artifact_hash": "abc123",
        "decision": "approved",
        "approved_at": "2026-08-31T17:30:00+09:00",
        "comment": "Human approved the implementation plan.",
    }