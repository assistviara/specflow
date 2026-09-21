from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from application.codex_execution import (
    CodexCommandEvent,
)
from application.execution_record_builder import (
    build_test_execution_record,
)


def test_builder_creates_record_from_explicit_test_phases():
    implementation_id = uuid4()
    recorded_at = datetime(
        2026,
        9,
        21,
        9,
        30,
        tzinfo=timezone.utc,
    )
    trace_path = Path(
        "projects/specflow/evidence/"
        f"codex_command_trace_{implementation_id}.jsonl"
    )
    command_events = (
        CodexCommandEvent(
            event_order=1,
            item_id="item_initial",
            command=(
                "specflow-test --phase initial -- "
                "python -m pytest tests/test_example.py"
            ),
            status="completed",
            exit_code=1,
            output="1 failed\n",
            test_phase="initial",
        ),
        CodexCommandEvent(
            event_order=2,
            item_id="item_target",
            command=(
                "specflow-test --phase target -- "
                "python -m pytest tests/test_example.py"
            ),
            status="completed",
            exit_code=0,
            output="1 passed\n",
            test_phase="target",
        ),
        CodexCommandEvent(
            event_order=3,
            item_id="item_full",
            command=(
                "specflow-test --phase full -- "
                "python -m pytest"
            ),
            status="completed",
            exit_code=0,
            output="417 passed\n",
            test_phase="full",
        ),
    )

    record = build_test_execution_record(
        implementation_id=implementation_id,
        recorded_at=recorded_at,
        command_events=command_events,
        test_required=True,
        tests_created_or_modified=(
            "tests/test_example.py",
        ),
        command_trace_path=trace_path,
        command_trace_sha256="a" * 64,
        errors=(),
        warnings=(),
        no_tdd_reason=None,
    )

    assert record.schema_version == "1"
    assert record.implementation_id == implementation_id
    assert record.recorded_at == recorded_at
    assert record.tests_created_or_modified == (
        "tests/test_example.py",
    )
    assert record.test_commands == tuple(
        event.command
        for event in command_events
    )

    assert record.initial_test.status == "COMPLETED"
    assert record.initial_test.result == "FAIL"
    assert record.target_test.status == "COMPLETED"
    assert record.target_test.result == "PASS"
    assert record.full_test.status == "COMPLETED"
    assert record.full_test.result == "PASS"

    assert record.errors == ()
    assert record.warnings == ()
    assert record.unavailable_evidence == ()
    assert record.no_tdd_reason is None
    assert record.command_trace_path == trace_path
    assert record.command_trace_sha256 == "a" * 64



def test_builder_marks_missing_required_test_phases_unavailable():
    implementation_id = uuid4()
    target_event = CodexCommandEvent(
        event_order=1,
        item_id="item_target",
        command=(
            "specflow-test --phase target -- "
            "python -m pytest tests/test_example.py"
        ),
        status="completed",
        exit_code=0,
        output="1 passed\n",
        test_phase="target",
    )

    record = build_test_execution_record(
        implementation_id=implementation_id,
        recorded_at=datetime.now(timezone.utc),
        command_events=(target_event,),
        test_required=True,
        tests_created_or_modified=(
            "tests/test_example.py",
        ),
        command_trace_path=Path(
            "projects/specflow/evidence/"
            f"codex_command_trace_{implementation_id}.jsonl"
        ),
        command_trace_sha256="b" * 64,
        errors=(),
        warnings=(),
        no_tdd_reason=None,
    )

    assert record.initial_test.status == "NOT_RUN"
    assert record.initial_test.result == "NONE"
    assert record.target_test.status == "COMPLETED"
    assert record.target_test.result == "PASS"
    assert record.full_test.status == "NOT_RUN"
    assert record.full_test.result == "NONE"
    assert record.unavailable_evidence == (
        "initial_test_result",
        "full_test_result",
    )
