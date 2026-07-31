from pathlib import Path
from typing import Protocol


class CommandExecutor(Protocol):
    """外部コマンドを実行するためのインターフェース。"""

    def run(
        self,
        command: list[str],
        *,
        cwd: Path,
        input_text: str,
    ) -> str:
        ...


class CodexRunner:
    """Codex CLIへプロンプトを渡し、生成結果を取得する。"""

    def __init__(self, command_executor: CommandExecutor) -> None:
        self._command_executor = command_executor

    def run(
        self,
        *,
        prompt: str,
        working_directory: Path,
    ) -> str:
        """指定した作業ディレクトリでCodexを実行する。"""

        return self._command_executor.run(
            ["codex"],
            cwd=working_directory,
            input_text=prompt,
        )