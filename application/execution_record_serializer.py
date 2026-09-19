from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from application.execution_record import (
    TestExecutionRecord,
    TestExecutionResult,
)


def execution_record_to_dict(
    record: TestExecutionRecord,
) -> dict[str, Any]:
    return {
        "schema_version": record.schema_version,
        "implementation_id": str(
            record.implementation_id
        ),
        "recorded_at": record.recorded_at.isoformat(),
        "tests_created_or_modified": list(
            record.tests_created_or_modified
        ),
        "test_commands": list(record.test_commands),
        "initial_test": {
            "status": record.initial_test.status,
            "result": record.initial_test.result,
        },
        "target_test": {
            "status": record.target_test.status,
            "result": record.target_test.result,
        },
        "full_test": {
            "status": record.full_test.status,
            "result": record.full_test.result,
        },
        "errors": list(record.errors),
        "warnings": list(record.warnings),
        "unavailable_evidence": list(
            record.unavailable_evidence
        ),
        "no_tdd_reason": record.no_tdd_reason,
        "command_trace_path": (
            record.command_trace_path.as_posix()
        ),
        "command_trace_sha256": (
            record.command_trace_sha256
        ),
    }


def _string_tuple(
    data: dict[str, Any],
    field_name: str,
) -> tuple[str, ...]:
    value = data[field_name]

    if not isinstance(value, list):
        raise ValueError(
            f"{field_name} must be a list"
        )

    if not all(
        isinstance(item, str)
        for item in value
    ):
        raise ValueError(
            f"{field_name} must contain only strings"
        )

    return tuple(value)


def execution_record_from_dict(
    data: dict[str, Any],
) -> TestExecutionRecord:
    initial_test = data["initial_test"]
    target_test = data["target_test"]
    full_test = data["full_test"]

    return TestExecutionRecord(
        schema_version=data["schema_version"],
        implementation_id=UUID(
            data["implementation_id"]
        ),
        recorded_at=datetime.fromisoformat(
            data["recorded_at"]
        ),
        tests_created_or_modified=_string_tuple(
            data,
            "tests_created_or_modified",
        ),
        test_commands=_string_tuple(
            data,
            "test_commands",
        ),
        initial_test=TestExecutionResult(
            status=initial_test["status"],
            result=initial_test["result"],
        ),
        target_test=TestExecutionResult(
            status=target_test["status"],
            result=target_test["result"],
        ),
        full_test=TestExecutionResult(
            status=full_test["status"],
            result=full_test["result"],
        ),
        errors=_string_tuple(
            data,
            "errors",
        ),
        warnings=_string_tuple(
            data,
            "warnings",
        ),
        unavailable_evidence=_string_tuple(
            data,
            "unavailable_evidence",
        ),
        no_tdd_reason=data["no_tdd_reason"],
        command_trace_path=Path(
            data["command_trace_path"]
        ),
        command_trace_sha256=data[
            "command_trace_sha256"
        ],
    )
