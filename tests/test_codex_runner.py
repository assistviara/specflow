from pathlib import Path

from core.ai.codex_runner import CodexRunner


class FakeCommandExecutor:
    def __init__(self) -> None:
        self.received_command: list[str] | None = None
        self.received_cwd: Path | None = None
        self.received_input: str | None = None

    def run(
        self,
        command: list[str],
        *,
        cwd: Path,
        input_text: str,
    ) -> str:
        self.received_command = command
        self.received_cwd = cwd
        self.received_input = input_text
        return "生成されたPlan"


def test_run_executes_codex_in_target_directory() -> None:
    executor = FakeCommandExecutor()
    runner = CodexRunner(command_executor=executor)
    target_path = Path("sample_project")

    result = runner.run(
        prompt="Planを作成してください。",
        working_directory=target_path,
    )

    assert executor.received_command == ["codex"]
    assert executor.received_cwd == target_path
    assert executor.received_input == "Planを作成してください。"
    assert result == "生成されたPlan"