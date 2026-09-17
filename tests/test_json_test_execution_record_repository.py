import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from application.execution_record import (
    TestExecutionRecord as ExecutionRecord,
    TestExecutionResult as ExecutionResult,
)
from infrastructure.json_test_execution_record_repository import (
    JsonTestExecutionRecordRepository,
)


def make_record() -> ExecutionRecord:
    implementation_id = uuid4()

    return ExecutionRecord(
        schema_version="1",
        implementation_id=implementation_id,
        recorded_at=datetime(
            2026,
            9,
            17,
            11,
            30,
            tzinfo=timezone.utc,
        ),
        tests_created_or_modified=(
            "tests/test_example.py",
        ),
        test_commands=(
            "python -m pytest tests/test_example.py",
        ),
        initial_test=ExecutionResult(
            status="COMPLETED",
            result="FAIL",
        ),
        target_test=ExecutionResult(
            status="COMPLETED",
            result="PASS",
        ),
        full_test=ExecutionResult(
            status="COMPLETED",
            result="PASS",
        ),
        errors=(),
        warnings=(),
        unavailable_evidence=(),
        no_tdd_reason=None,
        command_trace_path=Path(
            "projects/specflow/evidence/"
            f"codex_command_trace_{implementation_id}.jsonl"
        ),
        command_trace_sha256="a" * 64,
    )


def test_save_creates_canonical_json_file(
    tmp_path: Path,
) -> None:
    repository = JsonTestExecutionRecordRepository(
        tmp_path / "evidence"
    )
    record = make_record()

    saved_path = repository.save(record)

    expected_path = (
        tmp_path
        / "evidence"
        / f"test_execution_{record.implementation_id}.json"
    )

    assert saved_path == expected_path
    assert saved_path.exists()

    text = saved_path.read_text(encoding="utf-8")
    assert text.endswith("\n")

    data = json.loads(text)
    assert data["implementation_id"] == str(
        record.implementation_id
    )


def test_exists_reports_saved_record(
    tmp_path: Path,
) -> None:
    repository = JsonTestExecutionRecordRepository(
        tmp_path / "evidence"
    )
    record = make_record()

    assert repository.exists(
        record.implementation_id
    ) is False

    repository.save(record)

    assert repository.exists(
        record.implementation_id
    ) is True


def test_load_restores_saved_record(
    tmp_path: Path,
) -> None:
    repository = JsonTestExecutionRecordRepository(
        tmp_path / "evidence"
    )
    record = make_record()

    repository.save(record)

    restored = repository.load(
        record.implementation_id
    )

    assert restored == record


def test_load_missing_record_raises_file_not_found(
    tmp_path: Path,
) -> None:
    repository = JsonTestExecutionRecordRepository(
        tmp_path / "evidence"
    )

    with pytest.raises(FileNotFoundError):
        repository.load(uuid4())


def test_save_refuses_to_overwrite_existing_record(
    tmp_path: Path,
) -> None:
    repository = JsonTestExecutionRecordRepository(
        tmp_path / "evidence"
    )
    record = make_record()

    repository.save(record)

    with pytest.raises(FileExistsError):
        repository.save(record)
