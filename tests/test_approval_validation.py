import hashlib
from pathlib import Path

from core.approval_validation import validate_approval


def test_validate_approval_returns_false_when_record_does_not_exist():
    result = validate_approval(
        approval_record=None,
        current_artifact_path="dummy.md",
        current_artifact_type="implementation_plan",
    )

    assert result is False

def test_validate_approval_returns_false_when_decision_is_not_approved():
    result = validate_approval(
        approval_record={
            "artifact_type": "implementation_plan",
            "artifact_path": "dummy.md",
            "artifact_hash": "dummy-hash",
            "decision": "revision_required",
        },
        current_artifact_path="dummy.md",
        current_artifact_type="implementation_plan",
    )

    assert result is False

def test_validate_approval_returns_true_when_approval_matches_current_artifact(
    tmp_path: Path,
):
    artifact_file = tmp_path / "plan.md"
    artifact_file.write_text("approved plan", encoding="utf-8")

    artifact_hash = hashlib.sha256(
        artifact_file.read_bytes()
    ).hexdigest()

    result = validate_approval(
        approval_record={
            "artifact_type": "implementation_plan",
            "artifact_path": str(artifact_file),
            "artifact_hash": artifact_hash,
            "decision": "approved",
        },
        current_artifact_path=str(artifact_file),
        current_artifact_type="implementation_plan",
    )

    assert result is True

def test_validate_approval_returns_false_when_artifact_type_does_not_match():
    result = validate_approval(
        approval_record={
            "artifact_type": "specification",
            "artifact_path": "dummy.md",
            "artifact_hash": "dummy-hash",
            "decision": "approved",
        },
        current_artifact_path="dummy.md",
        current_artifact_type="implementation_plan",
    )

    assert result is False

def test_validate_approval_returns_false_when_artifact_path_does_not_match():
    result = validate_approval(
        approval_record={
            "artifact_type": "implementation_plan",
            "artifact_path": "old_plan.md",
            "artifact_hash": "dummy-hash",
            "decision": "approved",
        },
        current_artifact_path="current_plan.md",
        current_artifact_type="implementation_plan",
    )

    assert result is False

def test_validate_approval_returns_false_when_artifact_hash_does_not_match(
    tmp_path: Path,
):
    artifact_file = tmp_path / "plan.md"
    artifact_file.write_text("current plan", encoding="utf-8")

    result = validate_approval(
        approval_record={
            "artifact_type": "implementation_plan",
            "artifact_path": str(artifact_file),
            "artifact_hash": hashlib.sha256(
                b"approved plan"
            ).hexdigest(),
            "decision": "approved",
        },
        current_artifact_path=str(artifact_file),
        current_artifact_type="implementation_plan",
    )

    assert result is False

def test_validate_approval_returns_false_when_current_artifact_does_not_exist(
    tmp_path: Path,
):
    artifact_file = tmp_path / "missing_plan.md"

    result = validate_approval(
        approval_record={
            "artifact_type": "implementation_plan",
            "artifact_path": str(artifact_file),
            "artifact_hash": "dummy-hash",
            "decision": "approved",
        },
        current_artifact_path=str(artifact_file),
        current_artifact_type="implementation_plan",
    )

    assert result is False

def test_validate_approval_result_returns_structured_result_for_valid_approval(
    tmp_path,
):
    from core.approval_validation import validate_approval_result

    artifact_path = tmp_path / "implementation_plan.md"
    artifact_path.write_text(
        "approved implementation plan",
        encoding="utf-8",
    )

    import hashlib

    artifact_hash = hashlib.sha256(
        artifact_path.read_bytes()
    ).hexdigest()

    approval_record = {
        "approval_id": "plan-approval-001",
        "artifact_type": "implementation_plan",
        "artifact_path": str(artifact_path),
        "artifact_hash": artifact_hash,
        "decision": "approved",
        "approved_at": "2026-09-04T22:00:00+09:00",
        "comment": "Approved by Human.",
    }

    result = validate_approval_result(
        approval_record,
        str(artifact_path),
        "implementation_plan",
    )

    assert result.is_valid is True
    assert result.approval_id == "plan-approval-001"
    assert result.artifact_type == "implementation_plan"
    assert result.validation_errors == []
    assert result.validation_warnings == []

def test_validate_approval_result_reports_non_approved_decision(
    tmp_path,
):
    from core.approval_validation import validate_approval_result

    artifact_path = tmp_path / "implementation_plan.md"
    artifact_path.write_text(
        "implementation plan",
        encoding="utf-8",
    )

    import hashlib

    artifact_hash = hashlib.sha256(
        artifact_path.read_bytes()
    ).hexdigest()

    approval_record = {
        "approval_id": "plan-approval-001",
        "artifact_type": "implementation_plan",
        "artifact_path": str(artifact_path),
        "artifact_hash": artifact_hash,
        "decision": "revision_requested",
        "approved_at": "2026-09-04T22:00:00+09:00",
        "comment": "Please revise the plan.",
    }

    result = validate_approval_result(
        approval_record,
        str(artifact_path),
        "implementation_plan",
    )

    assert result.is_valid is False
    assert result.approval_id == "plan-approval-001"
    assert result.artifact_type == "implementation_plan"
    assert result.validation_errors == [
        "approval decision is not approved"
    ]
    assert result.validation_warnings == []

def test_validate_approval_result_reports_artifact_type_mismatch(
    tmp_path,
):
    from core.approval_validation import validate_approval_result

    artifact_path = tmp_path / "implementation_plan.md"
    artifact_path.write_text(
        "approved implementation plan",
        encoding="utf-8",
    )

    import hashlib

    artifact_hash = hashlib.sha256(
        artifact_path.read_bytes()
    ).hexdigest()

    approval_record = {
        "approval_id": "plan-approval-001",
        "artifact_type": "specification",
        "artifact_path": str(artifact_path),
        "artifact_hash": artifact_hash,
        "decision": "approved",
        "approved_at": "2026-09-04T22:00:00+09:00",
        "comment": "Approved by Human.",
    }

    result = validate_approval_result(
        approval_record,
        str(artifact_path),
        "implementation_plan",
    )

    assert result.is_valid is False
    assert result.approval_id == "plan-approval-001"
    assert result.artifact_type == "specification"
    assert result.validation_errors == [
        "artifact type does not match"
    ]
    assert result.validation_warnings == []

def test_validate_approval_result_reports_artifact_path_mismatch(
    tmp_path,
):
    from core.approval_validation import validate_approval_result

    artifact_path = tmp_path / "implementation_plan.md"
    artifact_path.write_text(
        "approved implementation plan",
        encoding="utf-8",
    )

    approval_record = {
        "approval_id": "plan-approval-001",
        "artifact_type": "implementation_plan",
        "artifact_path": str(tmp_path / "different_plan.md"),
        "artifact_hash": "unused-for-this-test",
        "decision": "approved",
        "approved_at": "2026-09-04T22:00:00+09:00",
        "comment": "Approved by Human.",
    }

    result = validate_approval_result(
        approval_record,
        str(artifact_path),
        "implementation_plan",
    )

    assert result.is_valid is False
    assert result.approval_id == "plan-approval-001"
    assert result.artifact_type == "implementation_plan"
    assert result.validation_errors == [
        "artifact path does not match"
    ]
    assert result.validation_warnings == []

def test_validate_approval_result_reports_hash_calculation_failure(
    tmp_path,
):
    from core.approval_validation import validate_approval_result

    artifact_path = tmp_path / "missing_plan.md"

    approval_record = {
        "approval_id": "plan-approval-001",
        "artifact_type": "implementation_plan",
        "artifact_path": str(artifact_path),
        "artifact_hash": "stored-hash",
        "decision": "approved",
        "approved_at": "2026-09-04T22:00:00+09:00",
        "comment": "Approved by Human.",
    }

    result = validate_approval_result(
        approval_record,
        str(artifact_path),
        "implementation_plan",
    )

    assert result.is_valid is False
    assert result.approval_id == "plan-approval-001"
    assert result.artifact_type == "implementation_plan"
    assert result.validation_errors == [
        "artifact hash could not be calculated"
    ]
    assert result.validation_warnings == []

def test_validate_approval_result_reports_artifact_hash_mismatch(
    tmp_path,
):
    from core.approval_validation import validate_approval_result

    artifact_path = tmp_path / "implementation_plan.md"
    artifact_path.write_text(
        "modified implementation plan",
        encoding="utf-8",
    )

    approval_record = {
        "approval_id": "plan-approval-001",
        "artifact_type": "implementation_plan",
        "artifact_path": str(artifact_path),
        "artifact_hash": "hash-from-approved-version",
        "decision": "approved",
        "approved_at": "2026-09-04T22:00:00+09:00",
        "comment": "Approved by Human.",
    }

    result = validate_approval_result(
        approval_record,
        str(artifact_path),
        "implementation_plan",
    )

    assert result.is_valid is False
    assert result.approval_id == "plan-approval-001"
    assert result.artifact_type == "implementation_plan"
    assert result.validation_errors == [
        "artifact hash does not match"
    ]
    assert result.validation_warnings == []