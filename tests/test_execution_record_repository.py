from typing import Protocol

from application.execution_record_repository import (
    TestExecutionRecordRepository as ExecutionRecordRepository,
)


def test_execution_record_repository_is_protocol() -> None:
    assert issubclass(
        ExecutionRecordRepository,
        Protocol,
    )


def test_execution_record_repository_exposes_required_methods(
) -> None:
    assert "save" in ExecutionRecordRepository.__dict__
    assert "load" in ExecutionRecordRepository.__dict__
    assert "exists" in ExecutionRecordRepository.__dict__
