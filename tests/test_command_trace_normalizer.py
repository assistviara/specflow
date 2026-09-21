from infrastructure.codex_jsonl_parser import (
    CodexCommandEvent,
)
from infrastructure.command_trace_normalizer import (
    normalize_command_trace,
)


def test_normalize_preserves_command_execution_facts():
    command_event = CodexCommandEvent(
        event_order=1,
        item_id="item_1",
        command=(
            "python -m "
            "infrastructure.specflow_test_wrapper "
            "--phase target -- "
            "python -m pytest tests/test_example.py"
        ),
        status="completed",
        exit_code=0,
        output="1 passed in 0.03s\n",
        test_phase="target",
    )

    result = normalize_command_trace(
        (command_event,)
    )

    assert len(result) == 1

    trace_event = result[0]
    assert trace_event.event_order == 1
    assert trace_event.test_phase == "target"
    assert trace_event.command == command_event.command
    assert trace_event.command_status == "completed"
    assert trace_event.exit_code == 0
    assert trace_event.output == "1 passed in 0.03s\n"
    assert trace_event.redacted_fields == ()



def test_normalize_redacts_sensitive_command_and_output():
    command_event = CodexCommandEvent(
        event_order=1,
        item_id="item_sensitive",
        command=(
            "OPENAI_API_KEY=sk-example-secret "
            "python -m pytest"
        ),
        status="completed",
        exit_code=0,
        output=(
            "Authorization: Bearer "
            "example-access-token"
        ),
        test_phase="target",
    )

    result = normalize_command_trace(
        (command_event,)
    )

    trace_event = result[0]
    assert trace_event.command == "[REDACTED]"
    assert trace_event.output == "[REDACTED]"
    assert trace_event.redacted_fields == (
        "command",
        "output",
    )
