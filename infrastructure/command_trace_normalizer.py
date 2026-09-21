import re
from dataclasses import dataclass

from infrastructure.codex_jsonl_parser import (
    CodexCommandEvent,
)


@dataclass(frozen=True)
class NormalizedCommandTraceEvent:
    event_order: int
    test_phase: str | None
    command: str
    command_status: str
    exit_code: int | None
    output: str
    redacted_fields: tuple[str, ...]


_SENSITIVE_PATTERNS = (
    re.compile(
        r"\b[A-Z0-9_]*"
        r"(?:API_KEY|TOKEN|PASSWORD|SECRET|CREDENTIAL)"
        r"[A-Z0-9_]*\s*=",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bAuthorization\s*:\s*Bearer\s+\S+",
        re.IGNORECASE,
    ),
    re.compile(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:postgresql|postgres|mysql)://"
        r"[^:\s/]+:[^@\s/]+@",
        re.IGNORECASE,
    ),
)


def _contains_sensitive_data(
    value: str,
) -> bool:
    return any(
        pattern.search(value) is not None
        for pattern in _SENSITIVE_PATTERNS
    )


def _normalize_event(
    event: CodexCommandEvent,
) -> NormalizedCommandTraceEvent:
    command = event.command
    output = event.output
    redacted_fields: list[str] = []

    if _contains_sensitive_data(command):
        command = "[REDACTED]"
        redacted_fields.append("command")

    if _contains_sensitive_data(output):
        output = "[REDACTED]"
        redacted_fields.append("output")

    return NormalizedCommandTraceEvent(
        event_order=event.event_order,
        test_phase=event.test_phase,
        command=command,
        command_status=event.status,
        exit_code=event.exit_code,
        output=output,
        redacted_fields=tuple(redacted_fields),
    )


def normalize_command_trace(
    command_events: tuple[
        CodexCommandEvent,
        ...,
    ],
) -> tuple[
    NormalizedCommandTraceEvent,
    ...,
]:
    return tuple(
        _normalize_event(event)
        for event in command_events
    )
