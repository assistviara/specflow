from pathlib import Path

from application.codex_implementation_adapter import (
    CodexImplementationAdapter,
)
from infrastructure.codex_jsonl_parser import (
    parse_codex_jsonl,
)


class FakeCodexRunner:
    def __init__(self) -> None:
        self.received_prompt: str | None = None
        self.received_working_directory: Path | None = None

    def run(
        self,
        *,
        prompt: str,
        working_directory: Path,
    ) -> str:
        self.received_prompt = prompt
        self.received_working_directory = working_directory
        return (
            '{"type":"thread.started",'
            '"thread_id":"thread-001"}\n'
            '{"type":"turn.started"}\n'
            '{"type":"item.completed","item":{'
            '"id":"item_1",'
            '"type":"agent_message",'
            '"text":"raw implementation result"}}\n'
            '{"type":"turn.completed","usage":{}}'
        )


def test_adapter_returns_parsed_codex_execution_result() -> None:
    runner = FakeCodexRunner()
    adapter = CodexImplementationAdapter(
        runner,
        trace_parser=parse_codex_jsonl,
    )

    result = adapter.run(
        prompt="implement approved scope",
        working_directory=Path("project"),
    )

    assert result.final_message == (
        "raw implementation result"
    )
    assert result.command_events == ()
    assert result.errors == ()

    assert runner.received_prompt == (
        "implement approved scope"
    )
    assert runner.received_working_directory == Path(
        "project"
    )
