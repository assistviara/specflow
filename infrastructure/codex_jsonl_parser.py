import json
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class CodexCommandEvent:
    event_order: int
    item_id: str
    command: str
    status: str
    exit_code: int | None
    output: str
    test_phase: str | None


@dataclass(frozen=True)
class CodexJsonlParseResult:
    command_events: tuple[CodexCommandEvent, ...]
    final_message: str | None
    errors: tuple[str, ...]



_EXPLICIT_TEST_PHASE_PATTERN = re.compile(
    r"(?:specflow-test|"
    r"infrastructure[.]specflow_test_wrapper)"
    r"\s+--phase\s+"
    r"([^\s]+)"
    r"(?=\s|$)"
)

_TEST_PHASE_PATTERN = re.compile(
    r"(?:specflow-test|"
    r"infrastructure[.]specflow_test_wrapper)"
    r"\s+--phase\s+"
    r"(initial|target|full)"
    r"(?=\s|$)"
)


def _extract_explicit_test_phase(
    command: str,
) -> str | None:
    match = _EXPLICIT_TEST_PHASE_PATTERN.search(
        command
    )
    if match is None:
        return None
    return match.group(1)


def _extract_test_phase(
    command: str,
) -> str | None:
    match = _TEST_PHASE_PATTERN.search(command)
    if match is None:
        return None
    return match.group(1)


def parse_codex_jsonl(
    raw_jsonl: str,
) -> CodexJsonlParseResult:
    command_events: list[CodexCommandEvent] = []
    final_message: str | None = None
    errors: list[str] = []

    def preserve_error(message: object) -> None:
        if (
            isinstance(message, str)
            and message
            and message not in errors
        ):
            errors.append(message)

    for line_number, line in enumerate(
        raw_jsonl.splitlines(),
        start=1,
    ):
        if not line.strip():
            continue

        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            preserve_error(
                "invalid JSONL event at line "
                f"{line_number}"
            )
            continue

        event_type = event.get("type")

        if event_type == "error":
            preserve_error(event.get("message"))
            continue

        if event_type == "turn.failed":
            error = event.get("error")

            if isinstance(error, dict):
                preserve_error(
                    error.get("message")
                )

            continue

        if event_type != "item.completed":
            continue

        item = event.get("item")

        if not isinstance(item, dict):
            continue

        item_type = item.get("type")

        if item_type == "command_execution":
            command = item["command"]
            test_phase = _extract_test_phase(
                command
            )
            explicit_phase = (
                _extract_explicit_test_phase(
                    command
                )
            )

            if (
                explicit_phase is not None
                and test_phase is None
            ):
                preserve_error(
                    "invalid test phase tag in "
                    "command event "
                    f"{item['id']}: "
                    f"{explicit_phase}"
                )

            command_events.append(
                CodexCommandEvent(
                    event_order=(
                        len(command_events) + 1
                    ),
                    item_id=item["id"],
                    command=command,
                    status=item["status"],
                    exit_code=item["exit_code"],
                    output=item["aggregated_output"],
                    test_phase=test_phase,
                )
            )
        elif item_type == "agent_message":
            final_message = item.get("text")
        elif item_type == "error":
            preserve_error(
                item.get("message")
            )

    return CodexJsonlParseResult(
        command_events=tuple(command_events),
        final_message=final_message,
        errors=tuple(errors),
    )
