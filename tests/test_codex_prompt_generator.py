from pathlib import Path

from core.codex_prompt_generator import CodexPromptGenerator
from core.prompt_builder import PromptResult


class FakeDocumentLoader:
    def load(self, path: Path) -> str:
        return f"CONTENT:{path.name}"


class FakePromptBuilder:
    def build(
        self,
        template: str,
        context: dict[str, object],
    ) -> PromptResult:
        return PromptResult(
            content="CODEX PROMPT",
            undefined_variables=[],
            unused_context=[],
            warnings=[],
        )


def test_generate_returns_prompt_result() -> None:
    generator = CodexPromptGenerator(
        document_loader=FakeDocumentLoader(),
        prompt_builder=FakePromptBuilder(),
    )

    result = generator.generate(
        specification_path=Path("specification.md"),
        implementation_plan_path=Path("implementation_plan.md"),
        implementation_target_path=Path("application"),
        tdd_rules="Use TDD.",
        completion_conditions="Required tests pass.",
        stop_conditions="Stop when scope expansion is required.",
        execution_result_reporting_requirements=(
            "Report changed files and test results."
        ),
        template_path=Path("implement_prompt_template.md"),
    )

    assert isinstance(result, PromptResult)
    assert result.content == "CODEX PROMPT"
    assert result.is_ready is True


def test_generate_builds_expected_context() -> None:
    class RecordingPromptBuilder:
        def __init__(self) -> None:
            self.template: str | None = None
            self.context: dict[str, object] | None = None

        def build(
            self,
            template: str,
            context: dict[str, object],
        ) -> PromptResult:
            self.template = template
            self.context = context
            return PromptResult(
                content="CODEX PROMPT",
                undefined_variables=[],
                unused_context=[],
                warnings=[],
            )

    prompt_builder = RecordingPromptBuilder()

    generator = CodexPromptGenerator(
        document_loader=FakeDocumentLoader(),
        prompt_builder=prompt_builder,
    )

    generator.generate(
        specification_path=Path("specification.md"),
        implementation_plan_path=Path("implementation_plan.md"),
        implementation_target_path=Path("application"),
        tdd_rules="Use TDD.",
        completion_conditions="Required tests pass.",
        stop_conditions="Stop when scope expansion is required.",
        execution_result_reporting_requirements=(
            "Report changed files and test results."
        ),
        template_path=Path("implement_prompt_template.md"),
    )

    assert prompt_builder.template == (
        "CONTENT:implement_prompt_template.md"
    )
    assert prompt_builder.context == {
        "SPECIFICATION": "CONTENT:specification.md",
        "IMPLEMENTATION_PLAN": "CONTENT:implementation_plan.md",
        "IMPLEMENTATION_TARGET_PATH": "application",
        "TDD_RULES": "Use TDD.",
        "COMPLETION_CONDITIONS": "Required tests pass.",
        "STOP_CONDITIONS": (
            "Stop when scope expansion is required."
        ),
        "EXECUTION_RESULT_REPORTING_REQUIREMENTS": (
            "Report changed files and test results."
        ),
    }
