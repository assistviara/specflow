import json

from infrastructure.codex_jsonl_parser import (
    parse_codex_jsonl,
)


def test_parse_extracts_completed_command_and_final_message():
    events = (
        {
            "type": "thread.started",
            "thread_id": "thread-001",
        },
        {
            "type": "turn.started",
        },
        {
            "type": "item.completed",
            "item": {
                "id": "item_0",
                "type": "agent_message",
                "text": "Running the command.",
            },
        },
        {
            "type": "item.started",
            "item": {
                "id": "item_1",
                "type": "command_execution",
                "command": "python --version",
                "aggregated_output": "",
                "exit_code": None,
                "status": "in_progress",
            },
        },
        {
            "type": "item.completed",
            "item": {
                "id": "item_1",
                "type": "command_execution",
                "command": "python --version",
                "aggregated_output": "Python 3.13.5\r\n",
                "exit_code": 0,
                "status": "completed",
            },
        },
        {
            "type": "item.completed",
            "item": {
                "id": "item_2",
                "type": "agent_message",
                "text": "TRACE_OK",
            },
        },
        {
            "type": "turn.completed",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 10,
            },
        },
    )
    raw_jsonl = "\n".join(
        json.dumps(event)
        for event in events
    )

    result = parse_codex_jsonl(raw_jsonl)

    assert len(result.command_events) == 1

    command_event = result.command_events[0]
    assert command_event.event_order == 1
    assert command_event.item_id == "item_1"
    assert command_event.command == "python --version"
    assert command_event.status == "completed"
    assert command_event.exit_code == 0
    assert command_event.output == "Python 3.13.5\r\n"

    assert result.final_message == "TRACE_OK"
    assert result.errors == ()



def test_parse_preserves_trace_errors_without_duplicating_messages():
    request_error = (
        "The configured model requires a newer "
        "version of Codex."
    )
    events = (
        {
            "type": "thread.started",
            "thread_id": "thread-002",
        },
        {
            "type": "item.completed",
            "item": {
                "id": "item_0",
                "type": "error",
                "message": (
                    "Model metadata was not found."
                ),
            },
        },
        {
            "type": "turn.started",
        },
        {
            "type": "error",
            "message": request_error,
        },
        {
            "type": "turn.failed",
            "error": {
                "message": request_error,
            },
        },
    )
    raw_jsonl = "\n".join(
        json.dumps(event)
        for event in events
    )

    result = parse_codex_jsonl(raw_jsonl)

    assert result.command_events == ()
    assert result.final_message is None
    assert result.errors == (
        "Model metadata was not found.",
        request_error,
    )



def test_parse_preserves_valid_events_when_one_jsonl_line_is_invalid():
    completed_command = {
        "type": "item.completed",
        "item": {
            "id": "item_1",
            "type": "command_execution",
            "command": "python --version",
            "aggregated_output": "Python 3.13.5",
            "exit_code": 0,
            "status": "completed",
        },
    }
    final_message = {
        "type": "item.completed",
        "item": {
            "id": "item_2",
            "type": "agent_message",
            "text": "TRACE_OK",
        },
    }
    raw_jsonl = "\n".join(
        (
            json.dumps(completed_command),
            "{invalid json",
            json.dumps(final_message),
        )
    )

    result = parse_codex_jsonl(raw_jsonl)

    assert len(result.command_events) == 1
    assert result.command_events[0].command == (
        "python --version"
    )
    assert result.final_message == "TRACE_OK"
    assert result.errors == (
        "invalid JSONL event at line 2",
    )



def test_parse_extracts_explicit_test_phase_from_wrapper_command():
    phases = ("initial", "target", "full")
    events = tuple(
        {
            "type": "item.completed",
            "item": {
                "id": f"item_{index}",
                "type": "command_execution",
                "command": (
                    "python -m "
                    "infrastructure.specflow_test_wrapper "
                    f"--phase {phase} -- "
                    "python -m pytest tests/test_foo.py"
                ),
                "aggregated_output": "test output",
                "exit_code": 0,
                "status": "completed",
            },
        }
        for index, phase in enumerate(
            phases,
            start=1,
        )
    )
    raw_jsonl = "\n".join(
        json.dumps(event)
        for event in events
    )

    result = parse_codex_jsonl(raw_jsonl)

    assert tuple(
        event.test_phase
        for event in result.command_events
    ) == phases
    assert result.errors == ()



def test_parse_preserves_invalid_explicit_test_phase():
    event = {
        "type": "item.completed",
        "item": {
            "id": "item_invalid_phase",
            "type": "command_execution",
            "command": (
                "python -m "
                "infrastructure.specflow_test_wrapper "
                "--phase smoke -- "
                "python -m pytest"
            ),
            "aggregated_output": "test output",
            "exit_code": 0,
            "status": "completed",
        },
    }

    result = parse_codex_jsonl(
        json.dumps(event)
    )

    assert len(result.command_events) == 1
    assert result.command_events[0].test_phase is None
    assert result.errors == (
        "invalid test phase tag in command event "
        "item_invalid_phase: smoke",
    )
