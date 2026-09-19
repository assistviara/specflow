import hashlib

import pytest
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from application.execution_record import (
    TestExecutionRecord as ExecutionRecord,
    TestExecutionResult as ExecutionResult,
)
from infrastructure.json_test_execution_record_repository import (
    JsonTestExecutionRecordRepository,
)
from infrastructure.json_test_state_provider import (
    JsonTestStateProvider,
)


def test_get_state_reads_verified_execution_record(
    tmp_path: Path,
) -> None:
    implementation_id = uuid4()
    evidence_dir = tmp_path / "evidence"

    trace_path = (
        evidence_dir
        / f"codex_command_trace_{implementation_id}.jsonl"
    )
    trace_bytes = (
        b'{"event_order":1,"test_phase":"initial"}\n'
        b'{"event_order":2,"test_phase":"target"}\n'
        b'{"event_order":3,"test_phase":"full"}\n'
    )

    evidence_dir.mkdir(
        parents=True,
        exist_ok=True,
    )
    trace_path.write_bytes(trace_bytes)

    record = ExecutionRecord(
        schema_version="1",
        implementation_id=implementation_id,
        recorded_at=datetime(
            2026,
            9,
            18,
            12,
            0,
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
        warnings=("one warning",),
        unavailable_evidence=(),
        no_tdd_reason=None,
        command_trace_path=trace_path,
        command_trace_sha256=hashlib.sha256(
            trace_bytes
        ).hexdigest(),
    )

    record_path = JsonTestExecutionRecordRepository(
        evidence_dir
    ).save(record)

    provider = JsonTestStateProvider(
        record_path=record_path,
        expected_implementation_id=implementation_id,
    )

    state = provider.get_state()

    assert state.tests_created_or_modified == (
        "tests/test_example.py",
    )
    assert state.test_commands == (
        "python -m pytest tests/test_example.py",
        "python -m pytest",
    )
    assert state.initial_test_status == "COMPLETED"
    assert state.initial_test_result == "FAIL"
    assert state.target_test_status == "COMPLETED"
    assert state.target_test_result == "PASS"
    assert state.full_test_status == "COMPLETED"
    assert state.full_test_result == "PASS"
    assert state.errors == ()
    assert state.warnings == ("one warning",)
    assert state.unavailable_evidence == ()
    assert state.no_tdd_reason is None



def make_execution_record(
    *,
    implementation_id,
    trace_path,
    trace_sha256,
):
    return ExecutionRecord(
        schema_version="1",
        implementation_id=implementation_id,
        recorded_at=datetime(
            2026,
            9,
            18,
            12,
            0,
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
        command_trace_path=trace_path,
        command_trace_sha256=trace_sha256,
    )


def test_implementation_id_mismatch_raises_value_error(
    tmp_path: Path,
) -> None:
    recorded_implementation_id = uuid4()
    expected_implementation_id = uuid4()
    evidence_dir = tmp_path / "evidence"
    trace_path = (
        evidence_dir
        / (
            "codex_command_trace_"
            f"{recorded_implementation_id}.jsonl"
        )
    )
    trace_bytes = b'{"event_order":1}\n'

    evidence_dir.mkdir(
        parents=True,
        exist_ok=True,
    )
    trace_path.write_bytes(trace_bytes)

    record = make_execution_record(
        implementation_id=recorded_implementation_id,
        trace_path=trace_path,
        trace_sha256=hashlib.sha256(
            trace_bytes
        ).hexdigest(),
    )
    record_path = JsonTestExecutionRecordRepository(
        evidence_dir
    ).save(record)

    provider = JsonTestStateProvider(
        record_path=record_path,
        expected_implementation_id=(
            expected_implementation_id
        ),
    )

    with pytest.raises(
        ValueError,
        match="implementation_id",
    ):
        provider.get_state()


def test_missing_command_trace_raises_file_not_found(
    tmp_path: Path,
) -> None:
    implementation_id = uuid4()
    evidence_dir = tmp_path / "evidence"
    missing_trace_path = (
        evidence_dir
        / f"codex_command_trace_{implementation_id}.jsonl"
    )

    record = make_execution_record(
        implementation_id=implementation_id,
        trace_path=missing_trace_path,
        trace_sha256="0" * 64,
    )
    record_path = JsonTestExecutionRecordRepository(
        evidence_dir
    ).save(record)

    provider = JsonTestStateProvider(
        record_path=record_path,
        expected_implementation_id=implementation_id,
    )

    with pytest.raises(FileNotFoundError):
        provider.get_state()


def test_command_trace_hash_mismatch_raises_value_error(
    tmp_path: Path,
) -> None:
    implementation_id = uuid4()
    evidence_dir = tmp_path / "evidence"
    trace_path = (
        evidence_dir
        / f"codex_command_trace_{implementation_id}.jsonl"
    )

    evidence_dir.mkdir(
        parents=True,
        exist_ok=True,
    )
    trace_path.write_bytes(
        b'{"event_order":1}\n'
    )

    record = make_execution_record(
        implementation_id=implementation_id,
        trace_path=trace_path,
        trace_sha256="0" * 64,
    )
    record_path = JsonTestExecutionRecordRepository(
        evidence_dir
    ).save(record)

    provider = JsonTestStateProvider(
        record_path=record_path,
        expected_implementation_id=implementation_id,
    )

    with pytest.raises(
        ValueError,
        match="SHA-256",
    ):
        provider.get_state()



def test_noncanonical_command_trace_path_raises_value_error(
    tmp_path: Path,
) -> None:
    implementation_id = uuid4()
    evidence_dir = tmp_path / "evidence"
    noncanonical_trace_path = (
        evidence_dir / "unrelated_trace.jsonl"
    )
    trace_bytes = b'{"event_order":1}\n'

    evidence_dir.mkdir(
        parents=True,
        exist_ok=True,
    )
    noncanonical_trace_path.write_bytes(
        trace_bytes
    )

    record = make_execution_record(
        implementation_id=implementation_id,
        trace_path=noncanonical_trace_path,
        trace_sha256=hashlib.sha256(
            trace_bytes
        ).hexdigest(),
    )
    record_path = JsonTestExecutionRecordRepository(
        evidence_dir
    ).save(record)

    provider = JsonTestStateProvider(
        record_path=record_path,
        expected_implementation_id=implementation_id,
    )

    with pytest.raises(
        ValueError,
        match="command trace path",
    ):
        provider.get_state()



def test_command_trace_outside_record_directory_raises_value_error(
    tmp_path: Path,
) -> None:
    implementation_id = uuid4()
    evidence_dir = tmp_path / "evidence"
    outside_dir = tmp_path / "outside"
    outside_trace_path = (
        outside_dir
        / f"codex_command_trace_{implementation_id}.jsonl"
    )
    trace_bytes = b'{"event_order":1}\n'

    outside_dir.mkdir(
        parents=True,
        exist_ok=True,
    )
    outside_trace_path.write_bytes(
        trace_bytes
    )

    record = make_execution_record(
        implementation_id=implementation_id,
        trace_path=outside_trace_path,
        trace_sha256=hashlib.sha256(
            trace_bytes
        ).hexdigest(),
    )
    record_path = JsonTestExecutionRecordRepository(
        evidence_dir
    ).save(record)

    provider = JsonTestStateProvider(
        record_path=record_path,
        expected_implementation_id=implementation_id,
    )

    with pytest.raises(
        ValueError,
        match="command trace path",
    ):
        provider.get_state()



def test_missing_execution_record_raises_file_not_found(
    tmp_path: Path,
) -> None:
    provider = JsonTestStateProvider(
        record_path=(
            tmp_path
            / "evidence"
            / f"test_execution_{uuid4()}.json"
        ),
        expected_implementation_id=uuid4(),
    )

    with pytest.raises(FileNotFoundError):
        provider.get_state()


def test_malformed_execution_record_json_raises_error(
    tmp_path: Path,
) -> None:
    implementation_id = uuid4()
    record_path = (
        tmp_path
        / f"test_execution_{implementation_id}.json"
    )
    record_path.write_text(
        "{invalid json",
        encoding="utf-8",
    )

    provider = JsonTestStateProvider(
        record_path=record_path,
        expected_implementation_id=implementation_id,
    )

    with pytest.raises(ValueError):
        provider.get_state()


def test_non_object_execution_record_json_raises_value_error(
    tmp_path: Path,
) -> None:
    implementation_id = uuid4()
    record_path = (
        tmp_path
        / f"test_execution_{implementation_id}.json"
    )
    record_path.write_text(
        "[]",
        encoding="utf-8",
    )

    provider = JsonTestStateProvider(
        record_path=record_path,
        expected_implementation_id=implementation_id,
    )

    with pytest.raises(
        ValueError,
        match="JSON object",
    ):
        provider.get_state()
