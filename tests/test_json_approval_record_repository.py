import json
import pytest
from pathlib import Path

from infrastructure.json_approval_record_repository import (
    JsonApprovalRecordRepository,
)


def test_save_writes_approval_record_as_json(tmp_path: Path):
    approvals_dir = tmp_path / "approvals"
    repository = JsonApprovalRecordRepository(approvals_dir)

    record = {
        "approval_id": "approval-001",
        "artifact_type": "implementation_plan",
        "artifact_path": "projects/specflow/docs/drafts/application_layer_implementation_plan_v0.1.0-draft.md",
        "artifact_hash": "abc123",
        "decision": "approved",
        "approved_at": "2026-08-31T17:30:00+09:00",
        "comment": "Human approved the implementation plan.",
    }

    repository.save(record)

    saved_file = approvals_dir / "approval-001.json"

    assert saved_file.exists()
    assert json.loads(saved_file.read_text(encoding="utf-8")) == record

def test_get_reads_saved_approval_record(tmp_path: Path):
    approvals_dir = tmp_path / "approvals"
    repository = JsonApprovalRecordRepository(approvals_dir)

    record = {
        "approval_id": "approval-001",
        "artifact_type": "implementation_plan",
        "artifact_path": "projects/specflow/docs/drafts/application_layer_implementation_plan_v0.1.0-draft.md",
        "artifact_hash": "abc123",
        "decision": "approved",
        "approved_at": "2026-08-31T17:30:00+09:00",
        "comment": "Human approved the implementation plan.",
    }

    repository.save(record)

    loaded_record = repository.get("approval-001")

    assert loaded_record == record

def test_get_raises_error_when_approval_record_does_not_exist(tmp_path: Path):
    approvals_dir = tmp_path / "approvals"
    repository = JsonApprovalRecordRepository(approvals_dir)

    with pytest.raises(FileNotFoundError):
        repository.get("missing-approval")