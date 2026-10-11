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
        test_environment: tuple[Path, Path] | None = None,
    ) -> None:
        self._runner = runner
        self._trace_parser = trace_parser
        self._test_environment = test_environment

    def run(
        self,
        *,
        prompt: str,
        working_directory: Path,
    ) -> CodexJsonlParseResult:
        if self._test_environment is not None:
            python, module_root = self._test_environment
            prompt += (
                '\n\n## Explicit test wrapper execution environment\n'
                f'Human-selected test Python: {python}\n'
                f'SpecFlow module search root: {module_root}\n'
                f'Test working directory: {working_directory}\n'
                'Use the specified Python executable for both the wrapper and pytest. '
                'Supply the SpecFlow module search root through PYTHONPATH only in the '
                'test command child environment; preserve other existing search entries. '
                'Do not change global settings, the Flask server environment, or repository files. '
                'The wrapper command shape remains: '
                'python -m infrastructure.specflow_test_wrapper --phase <initial|target|full> -- <test command and arguments>. '
                'Replace python with the specified executable, quoted for the actual shell. '
                'Keep the approved phase requirements and run pytest with that executable using -m pytest. '
                'If the executable or wrapper cannot be accessed, STOP and report the facts. '
                'Do not install dependencies, copy the wrapper, relax sandbox permissions, '
                'fall back to another Python, or bypass the wrapper.\n')
        raw_jsonl = self._runner.run(
            prompt=prompt,
            working_directory=working_directory,
        )
        return self._trace_parser(raw_jsonl)
