import pytest

from core.prompt_builder import PromptBuilder, PromptResult
from core.template_engine import RenderResult, TemplateRenderError


class FakeTemplateEngine:
    def __init__(self, result: RenderResult) -> None:
        self.result = result
        self.called = False
        self.received_template: str | None = None
        self.received_context: dict[str, object] | None = None

    def render(
        self,
        template: str,
        context: dict[str, object],
    ) -> RenderResult:
        self.called = True
        self.received_template = template
        self.received_context = context
        return self.result


class ErrorTemplateEngine:
    def render(
        self,
        template: str,
        context: dict[str, object],
    ) -> RenderResult:
        raise TemplateRenderError(
            error_type="TEST_ERROR",
            cause="テスト用エラーです。",
            guidance="例外が伝播することを確認してください。",
        )


def test_can_create_prompt_builder() -> None:
    builder = PromptBuilder()

    assert builder is not None


def test_build_returns_prompt_result() -> None:
    builder = PromptBuilder()

    result = builder.build(
        template="Project: {{PROJECT_NAME}}",
        context={"PROJECT_NAME": "SpecFlow"},
    )

    assert isinstance(result, PromptResult)


def test_build_uses_standard_template_engine() -> None:
    builder = PromptBuilder()

    result = builder.build(
        template="Project: {{PROJECT_NAME}}",
        context={"PROJECT_NAME": "SpecFlow"},
    )

    assert result.content == "Project: SpecFlow"
    assert result.undefined_variables == []
    assert result.unused_context == []
    assert result.warnings == []


def test_prompt_result_is_ready_when_no_undefined_variables() -> None:
    result = PromptResult(
        content="完成Prompt",
        undefined_variables=[],
        unused_context=[],
        warnings=[],
    )

    assert result.is_ready is True


def test_prompt_result_is_not_ready_when_variable_is_undefined() -> None:
    result = PromptResult(
        content="{{PROJECT_NAME}}",
        undefined_variables=["PROJECT_NAME"],
        unused_context=[],
        warnings=["未定義変数です: PROJECT_NAME"],
    )

    assert result.is_ready is False


def test_build_copies_all_render_result_fields() -> None:
    render_result = RenderResult(
        content="生成されたPrompt",
        undefined_variables=["MISSING_VALUE"],
        unused_context=["UNUSED_VALUE"],
        warnings=[
            "未定義変数です: MISSING_VALUE",
            "使用されなかったContextです: UNUSED_VALUE",
        ],
    )
    fake_engine = FakeTemplateEngine(render_result)
    builder = PromptBuilder(template_engine=fake_engine)

    result = builder.build(
        template="{{MISSING_VALUE}}",
        context={"UNUSED_VALUE": "unused"},
    )

    assert result.content == render_result.content
    assert (
        result.undefined_variables
        == render_result.undefined_variables
    )
    assert result.unused_context == render_result.unused_context
    assert result.warnings == render_result.warnings


def test_build_uses_injected_template_engine() -> None:
    fake_engine = FakeTemplateEngine(
        RenderResult(
            content="Fake result",
            undefined_variables=[],
            unused_context=[],
            warnings=[],
        )
    )
    builder = PromptBuilder(template_engine=fake_engine)
    context = {"PROJECT_NAME": "SpecFlow"}

    result = builder.build(
        template="Original template",
        context=context,
    )

    assert fake_engine.called is True
    assert fake_engine.received_template == "Original template"
    assert fake_engine.received_context == context
    assert result.content == "Fake result"


def test_build_propagates_template_render_error() -> None:
    builder = PromptBuilder(
        template_engine=ErrorTemplateEngine()
    )

    with pytest.raises(TemplateRenderError) as exc_info:
        builder.build(
            template="{{PROJECT_NAME}}",
            context={},
        )

    assert exc_info.value.error_type == "TEST_ERROR"


def test_prompt_result_copies_lists_from_render_result() -> None:
    render_result = RenderResult(
        content="Prompt",
        undefined_variables=[],
        unused_context=[],
        warnings=[],
    )
    fake_engine = FakeTemplateEngine(render_result)
    builder = PromptBuilder(template_engine=fake_engine)

    result = builder.build(
        template="Prompt",
        context={},
    )

    assert result.undefined_variables is not render_result.undefined_variables
    assert result.unused_context is not render_result.unused_context
    assert result.warnings is not render_result.warnings