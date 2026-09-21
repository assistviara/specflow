import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from infrastructure.command_trace_normalizer import (
    NormalizedCommandTraceEvent,
)


@dataclass(frozen=True)
class SavedCommandTrace:
    path: Path
    sha256: str


class JsonCommandTraceRepository:
    def __init__(
        self,
        evidence_dir: Path,
    ) -> None:
        self._evidence_dir = evidence_dir

    def save(
        self,
        implementation_id: UUID,
        events: tuple[
            NormalizedCommandTraceEvent,
            ...,
        ],
    ) -> SavedCommandTrace:
        self._evidence_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        path = self._jsonl_path(
            implementation_id
        )
        content = self._serialize(events)

        with path.open("xb") as file:
            file.write(content)

        saved_bytes = path.read_bytes()

        return SavedCommandTrace(
            path=path,
            sha256=hashlib.sha256(
                saved_bytes
            ).hexdigest(),
        )

    @staticmethod
    def _serialize(
        events: tuple[
            NormalizedCommandTraceEvent,
            ...,
        ],
    ) -> bytes:
        lines = (
            json.dumps(
                {
                    "event_order": event.event_order,
                    "test_phase": event.test_phase,
                    "command": event.command,
                    "command_status": (
                        event.command_status
                    ),
                    "exit_code": event.exit_code,
                    "output": event.output,
                    "redacted_fields": list(
                        event.redacted_fields
                    ),
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
            for event in events
        )
        text = "".join(
            f"{line}\n"
            for line in lines
        )
        return text.encode("utf-8")

    def _jsonl_path(
        self,
        implementation_id: UUID,
    ) -> Path:
        return (
            self._evidence_dir
            / (
                "codex_command_trace_"
                f"{implementation_id}.jsonl"
            )
        )
