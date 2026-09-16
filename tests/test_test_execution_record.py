from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from application.execution_record import (
    TestExecutionRecord as ExecutionRecord,
    TestExecutionResult as ExecutionResult,
)


def make_record() -> ExecutionRecord:
    return ExecutionRecord(
        schema_version="1",
        implementation_id=uuid4(),
        recorded_at=datetime(
            2026,
            9,
            16,
            12,
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
        warnings=(),
        unavailable_evidence=(),
        no_tdd_reason=None,
        command_trace_path=Path(
            "projects/specflow/evidence/"
            "codex_command_trace_example.jsonl"
        ),
        command_trace_sha256="a" * 64,
    )


def test_test_execution_record_preserves_v1_structure() -> None:
    record = make_record()

    assert record.schema_version == "1"
    assert record.tests_created_or_modified == (
        "tests/test_example.py",
    )
    assert record.initial_test.status == "COMPLETED"
    assert record.initial_test.result == "FAIL"
    assert record.target_test.result == "PASS"
    assert record.full_test.result == "PASS"
    assert record.command_trace_path == Path(
        "projects/specflow/evidence/"
        "codex_command_trace_example.jsonl"
    )
    assert record.command_trace_sha256 == "a" * 64


def test_test_execution_record_and_result_are_frozen() -> None:
    record = make_record()

    with pytest.raises(FrozenInstanceError):
        record.schema_version = "2"

    with pytest.raises(FrozenInstanceError):
        record.initial_test.result = "PASS"



@pytest.mark.parametrize(
    ("status", "result"),
    [
        ("COMPLETED", "PASS"),
        ("COMPLETED", "FAIL"),
        ("ERROR", "NONE"),
        ("NOT_RUN", "NONE"),
    ],
)
def test_test_execution_result_accepts_valid_pair(
    status: str,
    result: str,
) -> None:
    execution_result = ExecutionResult(
        status=status,
        result=result,
    )

    assert execution_result.status == status
    assert execution_result.result == result


@pytest.mark.parametrize(
    ("status", "result"),
    [
        ("COMPLETED", "NONE"),
        ("ERROR", "PASS"),
        ("ERROR", "FAIL"),
        ("NOT_RUN", "PASS"),
        ("NOT_RUN", "FAIL"),
        ("UNKNOWN", "NONE"),
        ("COMPLETED", "UNKNOWN"),
    ],
)
def test_test_execution_result_rejects_invalid_pair(
    status: str,
    result: str,
) -> None:
    with pytest.raises(ValueError):
        ExecutionResult(
            status=status,
            result=result,
        )


def test_test_execution_record_rejects_invalid_schema_version() -> None:
    record = make_record()

    with pytest.raises(ValueError):
        ExecutionRecord(
            schema_version="2",
            implementation_id=record.implementation_id,
            recorded_at=record.recorded_at,
            tests_created_or_modified=(
                record.tests_created_or_modified
            ),
            test_commands=record.test_commands,
            initial_test=record.initial_test,
            target_test=record.target_test,
            full_test=record.full_test,
            errors=record.errors,
            warnings=record.warnings,
            unavailable_evidence=record.unavailable_evidence,
            no_tdd_reason=record.no_tdd_reason,
            command_trace_path=record.command_trace_path,
            command_trace_sha256=record.command_trace_sha256,
        )


def test_test_execution_record_rejects_naive_recorded_at() -> None:
    record = make_record()

    with pytest.raises(ValueError):
        ExecutionRecord(
            schema_version=record.schema_version,
            implementation_id=record.implementation_id,
            recorded_at=datetime(2026, 9, 16, 12, 30),
            tests_created_or_modified=(
                record.tests_created_or_modified
            ),
            test_commands=record.test_commands,
            initial_test=record.initial_test,
            target_test=record.target_test,
            full_test=record.full_test,
            errors=record.errors,
            warnings=record.warnings,
            unavailable_evidence=record.unavailable_evidence,
            no_tdd_reason=record.no_tdd_reason,
            command_trace_path=record.command_trace_path,
            command_trace_sha256=record.command_trace_sha256,
        )



def test_test_execution_record_rejects_invalid_implementation_id(
) -> None:
    record = make_record()

    with pytest.raises(ValueError):
        replace(
            record,
            implementation_id="not-a-uuid",
        )


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
def test_test_execution_record_rejects_non_string_tuple_item(
    field_name: str,
) -> None:
    record = make_record()

    with pytest.raises(ValueError):
        replace(
            record,
            **{field_name: ("valid", 123)},
        )


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
def test_test_execution_record_rejects_non_tuple_collection(
    field_name: str,
) -> None:
    record = make_record()

    with pytest.raises(ValueError):
        replace(
            record,
            **{field_name: ["value"]},
        )


def test_test_execution_record_rejects_invalid_no_tdd_reason(
) -> None:
    record = make_record()

    with pytest.raises(ValueError):
        replace(
            record,
            no_tdd_reason=123,
        )


def test_test_execution_record_rejects_invalid_trace_path(
) -> None:
    record = make_record()

    with pytest.raises(ValueError):
        replace(
            record,
            command_trace_path="trace.jsonl",
        )


@pytest.mark.parametrize(
    "invalid_hash",
    [
        "",
        "a" * 63,
        "a" * 65,
        "z" * 64,
    ],
)
def test_test_execution_record_rejects_invalid_trace_sha256(
    invalid_hash: str,
) -> None:
    record = make_record()

    with pytest.raises(ValueError):
        replace(
            record,
            command_trace_sha256=invalid_hash,
        )
