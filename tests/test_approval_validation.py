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