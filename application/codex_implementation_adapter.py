from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from application.codex_execution import (
    CodexJsonlParseResult,
)


class CodexImplementationRunner(Protocol):
    def run(
        self,
        *,
        prompt: str,
        working_directory: Path,
    ) -> str:
        ...


CodexExecutionTraceParser = Callable[
    [str],
    CodexJsonlParseResult,
]


class CodexImplementationAdapter:
    def __init__(
        self,
        runner: CodexImplementationRunner,
        *,
        trace_parser: CodexExecutionTraceParser,
    ) -> None:
        self._runner = runner
        self._trace_parser = trace_parser

    def run(
        self,
        *,
        prompt: str,
        working_directory: Path,
    ) -> CodexJsonlParseResult:
        raw_jsonl = self._runner.run(
            prompt=prompt,
            working_directory=working_directory,
        )
        return self._trace_parser(raw_jsonl)
