from pathlib import Path

from application.codex_implementation_adapter import (
    CodexImplementationAdapter,
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
        return "raw implementation result"


def test_adapter_passes_prompt_and_working_directory_to_runner() -> None:
    runner = FakeCodexRunner()
    adapter = CodexImplementationAdapter(runner)

    result = adapter.run(
        prompt="implement approved scope",
        working_directory=Path("project"),
    )

    assert result == "raw implementation result"
    assert runner.received_prompt == "implement approved scope"
    assert runner.received_working_directory == Path("project")
