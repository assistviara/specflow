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
    raw_jsonl: str
    command_events: tuple[CodexCommandEvent, ...]
    final_message: str | None
    process_succeeded: bool
    errors: tuple[str, ...]
