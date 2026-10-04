"""Transport only: no Workflow, approval, or retry decisions."""
from pathlib import Path
import subprocess


class SubprocessCommandExecutor:
    def run(self, command: list[str], *, cwd: Path, input_text: str) -> str:
        try:
            result = subprocess.run(
                command, cwd=cwd, input=input_text, shell=False,
                capture_output=True, text=True, encoding='utf-8', check=False,
            )
        except (OSError, UnicodeError):
            raise RuntimeError('Codex process could not be started or decoded; STOP.') from None
        if result.returncode != 0:
            # Never expose stderr (which can contain credentials or prompt data).
            raise RuntimeError(f'Codex process failed (exit {result.returncode}); STOP.')
        return result.stdout
