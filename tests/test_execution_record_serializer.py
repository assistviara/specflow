import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from application.execution_record import (
    TestExecutionRecord as ExecutionRecord,
    TestExecutionResult as ExecutionResult,
)
from application.execution_record_serializer import (
    execution_record_from_dict,
    execution_record_to_dict,
)


def make_record() -> ExecutionRecord:
    return ExecutionRecord(
        schema_version="1",
        implementation_id=uuid4(),
        recorded_at=datetime(
            2026,
            9,
            17,
            10,
            30,
            tzinfo=timezone.utc,
        ),
        tests_created_or_modified=(
            "tests/test_example.py",
        ),
        test_commands=(
            "python -m pytest tests/test_example.py",
            "python -m pytest",
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
        warnings=("example warning",),
        unavailable_evidence=(),
        no_tdd_reason=None,
        command_trace_path=Path(
            "projects/specflow/evidence/"
            "codex_command_trace_example.jsonl"
        ),
        command_trace_sha256="a" * 64,
    )


def test_execution_record_to_dict_uses_json_safe_values(
) -> None:
    record = make_record()

    data = execution_record_to_dict(record)

    assert data["schema_version"] == "1"
    assert data["implementation_id"] == str(
        record.implementation_id
    )
    assert data["recorded_at"] == (
        "2026-09-17T10:30:00+00:00"
    )
    assert data["tests_created_or_modified"] == [
        "tests/test_example.py",
    ]
    assert data["test_commands"] == [
        "python -m pytest tests/test_example.py",
        "python -m pytest",
    ]
    assert data["initial_test"] == {
        "status": "COMPLETED",
        "result": "FAIL",
    }
    assert data["target_test"] == {
        "status": "COMPLETED",
        "result": "PASS",
    }
    assert data["full_test"] == {
        "status": "COMPLETED",
        "result": "PASS",
    }
    assert data["errors"] == []
    assert data["warnings"] == ["example warning"]
    assert data["unavailable_evidence"] == []
    assert data["no_tdd_reason"] is None
    assert data["command_trace_path"] == (
        "projects/specflow/evidence/"
        "codex_command_trace_example.jsonl"
    )
    assert data["command_trace_sha256"] == "a" * 64

    json.dumps(data)


def test_test_execution_record_round_trip_restores_types(
) -> None:
    record = make_record()

    restored = execution_record_from_dict(
        execution_record_to_dict(record)
    )

    assert restored == record
    assert isinstance(
        restored.implementation_id,
        UUID,
    )
    assert isinstance(
        restored.recorded_at,
        datetime,
    )
    assert isinstance(
        restored.command_trace_path,
        Path,
    )
    assert isinstance(
        restored.tests_created_or_modified,
        tuple,
    )
    assert isinstance(
        restored.initial_test,
        ExecutionResult,
    )



def test_execution_record_round_trip_through_json(
) -> None:
    record = make_record()

    serialized = json.dumps(
        execution_record_to_dict(record),
        ensure_ascii=False,
    )
    data = json.loads(serialized)

    restored = execution_record_from_dict(data)

    assert restored == record


@pytest.mark.parametrize(
    "field_name",
    [
        "tests_created_or_modified",
        "test_commands",
        "errors",
        "warnings",
        "unavailable_evidence",
    ],
)
def test_execution_record_from_dict_rejects_non_array_field(
    field_name: str,
) -> None:
    data = execution_record_to_dict(make_record())
    data[field_name] = "not-an-array"

    with pytest.raises(
        ValueError,
        match=f"{field_name} must be a list",
    ):
        execution_record_from_dict(data)
