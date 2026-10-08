"""Codex executable resolution; execution remains the transport's responsibility."""
import os
from pathlib import Path
import sys

from core.ai.codex_runner import CommandExecutor


class CodexCommandExecutor:
    def __init__(self, transport: CommandExecutor) -> None:
        self._transport = transport

    def run(self, command: list[str], *, cwd: Path, input_text: str) -> str:
        argv = list(command)
        if sys.platform == 'win32':
            executable = self._resolve_windows_executable()
            if not argv or executable is None:
                raise RuntimeError('Codex executable could not be safely resolved; STOP.') from None
            argv[0] = executable
        return self._transport.run(argv, cwd=cwd, input_text=input_text)

    @staticmethod
    def _resolve_windows_executable() -> str | None:
        try:
            for entry in os.environ.get('PATH', '').split(os.pathsep):
                directory = Path(entry)
                # Never allow empty, drive-relative, or cwd-relative PATH entries.
                if not entry or not directory.is_absolute():
                    continue
                candidate = directory / 'codex.cmd'
                if candidate.is_file():
                    resolved = candidate.resolve(strict=True)
                    if resolved.is_absolute() and resolved.is_file():
                        return str(resolved)
        except (OSError, ValueError, RuntimeError):
            return None
        return None
