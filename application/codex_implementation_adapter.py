from pathlib import Path
from typing import Protocol


class CodexImplementationRunner(Protocol):
    def run(
        self,
        *,
        prompt: str,
        working_directory: Path,
    ) -> str:
        ...


class CodexImplementationAdapter:
    def __init__(
        self,
        runner: CodexImplementationRunner,
    ) -> None:
        self._runner = runner

    def run(
        self,
        *,
        prompt: str,
        working_directory: Path,
    ) -> str:
        return self._runner.run(
            prompt=prompt,
            working_directory=working_directory,
        )
