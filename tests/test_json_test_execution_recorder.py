from datetime import datetime, timezone
from uuid import uuid4

from application.codex_execution import (
    CodexCommandEvent,
)
from infrastructure.json_command_trace_repository import (
    JsonCommandTraceRepository,
)
from infrastructure.json_test_execution_record_repository import (
    JsonTestExecutionRecordRepository,
)
from infrastructure.json_test_execution_recorder import (
    JsonTestExecutionRecorder,
)


def test_record_saves_trace_before_test_execution_record(
    tmp_path,
):
    implementation_id = uuid4()
    evidence_dir = tmp_path / "evidence"
    trace_repository = JsonCommandTraceRepository(
        evidence_dir=evidence_dir
    )
    record_repository = (
        JsonTestExecutionRecordRepository(
            evidence_dir=evidence_dir
        )
    )
    recorder = JsonTestExecutionRecorder(
        trace_repository=trace_repository,
        record_repository=record_repository,
    )
    command_events = (
        CodexCommandEvent(
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
        ),
    )

    record_path = recorder.record(
        implementation_id=implementation_id,
        recorded_at=datetime.now(timezone.utc),
        command_events=command_events,
        test_required=True,
        tests_created_or_modified=(
            "tests/test_example.py",
        ),
        errors=(),
        warnings=(),
        no_tdd_reason=None,
    )

    trace_path = (
        evidence_dir
        / f"codex_command_trace_{implementation_id}.jsonl"
    )
    expected_record_path = (
        evidence_dir
        / f"test_execution_{implementation_id}.json"
    )

    assert trace_path.exists()
    assert record_path == expected_record_path
    assert record_path.exists()

    record = record_repository.load(
        implementation_id
    )
    assert record.command_trace_path == trace_path
    assert len(record.command_trace_sha256) == 64
    assert record.target_test.status == "COMPLETED"
    assert record.target_test.result == "PASS"
    assert record.unavailable_evidence == (
        "initial_test_result",
        "full_test_result",
    )
