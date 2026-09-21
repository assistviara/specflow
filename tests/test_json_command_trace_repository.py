import hashlib
import json

import pytest
from uuid import uuid4

from infrastructure.command_trace_normalizer import (
    NormalizedCommandTraceEvent,
)
from infrastructure.json_command_trace_repository import (
    JsonCommandTraceRepository,
)


def test_save_creates_jsonl_and_returns_its_sha256(
    tmp_path,
):
    implementation_id = uuid4()
    repository = JsonCommandTraceRepository(
        evidence_dir=tmp_path / "evidence"
    )
    events = (
        NormalizedCommandTraceEvent(
            event_order=1,
            test_phase="initial",
            command="python -m pytest tests/test_example.py",
            command_status="completed",
            exit_code=1,
            output="1 failed\n",
            redacted_fields=(),
        ),
        NormalizedCommandTraceEvent(
            event_order=2,
            test_phase="target",
            command="python -m pytest tests/test_example.py",
            command_status="completed",
            exit_code=0,
            output="1 passed\n",
            redacted_fields=(),
        ),
    )

    saved = repository.save(
        implementation_id,
        events,
    )

    expected_path = (
        tmp_path
        / "evidence"
        / f"codex_command_trace_{implementation_id}.jsonl"
    )
    saved_bytes = expected_path.read_bytes()

    assert saved.path == expected_path
    assert saved.sha256 == hashlib.sha256(
        saved_bytes
    ).hexdigest()

    records = tuple(
        json.loads(line)
        for line in saved_bytes.decode(
            "utf-8"
        ).splitlines()
    )
    assert records == (
        {
            "event_order": 1,
            "test_phase": "initial",
            "command": (
                "python -m pytest "
                "tests/test_example.py"
            ),
            "command_status": "completed",
            "exit_code": 1,
            "output": "1 failed\n",
            "redacted_fields": [],
        },
        {
            "event_order": 2,
            "test_phase": "target",
            "command": (
                "python -m pytest "
                "tests/test_example.py"
            ),
            "command_status": "completed",
            "exit_code": 0,
            "output": "1 passed\n",
            "redacted_fields": [],
        },
    )



def test_save_does_not_overwrite_existing_command_trace(
    tmp_path,
):
    implementation_id = uuid4()
    repository = JsonCommandTraceRepository(
        evidence_dir=tmp_path / "evidence"
    )
    original_events = (
        NormalizedCommandTraceEvent(
            event_order=1,
            test_phase="initial",
            command="original command",
            command_status="completed",
            exit_code=1,
            output="original output",
            redacted_fields=(),
        ),
    )
    replacement_events = (
        NormalizedCommandTraceEvent(
            event_order=1,
            test_phase="target",
            command="replacement command",
            command_status="completed",
            exit_code=0,
            output="replacement output",
            redacted_fields=(),
        ),
    )

    saved = repository.save(
        implementation_id,
        original_events,
    )
    original_bytes = saved.path.read_bytes()

    with pytest.raises(FileExistsError):
        repository.save(
            implementation_id,
            replacement_events,
        )

    assert saved.path.read_bytes() == original_bytes
