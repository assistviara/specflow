from pathlib import Path

import pytest

from core.template_engine import (
    RenderResult,
    TemplateEngine,
    TemplateRenderError,
)


def test_can_create_template_engine() -> None:
    engine = TemplateEngine()

    assert engine is not None


def test_render_returns_render_result() -> None:
    engine = TemplateEngine()

    result = engine.render(
        template="Project: {{PROJECT_NAME}}",
        context={"PROJECT_NAME": "SpecFlow"},
    )

    assert isinstance(result, RenderResult)


def test_render_replaces_single_variable() -> None:
    engine = TemplateEngine()

    result = engine.render(
        template="Project: {{PROJECT_NAME}}",
        context={"PROJECT_NAME": "SpecFlow"},
    )

    assert result.content == "Project: SpecFlow"
    assert result.undefined_variables == []
    assert result.unused_context == []
    assert result.warnings == []


def test_render_replaces_multiple_variables() -> None:
    engine = TemplateEngine()

    result = engine.render(
        template=(
            "Project: {{PROJECT_NAME}}\n"
            "Version: {{PROJECT_VERSION}}"
        ),
        context={
            "PROJECT_NAME": "SpecFlow",
            "PROJECT_VERSION": "0.1.0",
        },
    )

    assert "Project: SpecFlow" in result.content
    assert "Version: 0.1.0" in result.content


def test_render_replaces_same_variable_multiple_times() -> None:
    engine = TemplateEngine()

    result = engine.render(
        template="{{PROJECT_NAME}} / {{PROJECT_NAME}}",
        context={"PROJECT_NAME": "SpecFlow"},
    )

    assert result.content == "SpecFlow / SpecFlow"


def test_render_converts_number_to_string() -> None:
    engine = TemplateEngine()

    result = engine.render(
        template="Count: {{COUNT}}",
        context={"COUNT": 10},
    )

    assert result.content == "Count: 10"


def test_render_converts_path_to_string() -> None:
    engine = TemplateEngine()
    path = Path("projects/specflow")

    result = engine.render(
        template="Path: {{TARGET_PATH}}",
        context={"TARGET_PATH": path},
    )

    assert result.content == f"Path: {path}"


def test_render_keeps_undefined_variable() -> None:
    engine = TemplateEngine()

    result = engine.render(
        template="Project: {{PROJECT_NAME}}",
        context={},
    )

    assert result.content == "Project: {{PROJECT_NAME}}"
    assert result.undefined_variables == ["PROJECT_NAME"]
    assert any(
        "PROJECT_NAME" in warning
        for warning in result.warnings
    )


def test_render_keeps_variable_when_value_is_none() -> None:
    engine = TemplateEngine()

    result = engine.render(
        template="Project: {{PROJECT_NAME}}",
        context={"PROJECT_NAME": None},
    )

    assert result.content == "Project: {{PROJECT_NAME}}"
    assert result.undefined_variables == []
    assert any(
        "None" in warning
        for warning in result.warnings
    )


def test_render_detects_unused_context() -> None:
    engine = TemplateEngine()

    result = engine.render(
        template="Project: {{PROJECT_NAME}}",
        context={
            "PROJECT_NAME": "SpecFlow",
            "UNUSED_VALUE": "unused",
        },
    )

    assert result.unused_context == ["UNUSED_VALUE"]
    assert any(
        "UNUSED_VALUE" in warning
        for warning in result.warnings
    )


def test_render_template_without_variables() -> None:
    engine = TemplateEngine()
    template = "変数を含まないTemplateです。"

    result = engine.render(
        template=template,
        context={},
    )

    assert result.content == template
    assert result.undefined_variables == []
    assert result.unused_context == []
    assert result.warnings == []


def test_render_does_not_modify_original_template() -> None:
    engine = TemplateEngine()
    template = "Project: {{PROJECT_NAME}}"

    engine.render(
        template=template,
        context={"PROJECT_NAME": "SpecFlow"},
    )

    assert template == "Project: {{PROJECT_NAME}}"


def test_render_raises_when_template_is_empty() -> None:
    engine = TemplateEngine()

    with pytest.raises(TemplateRenderError) as exc_info:
        engine.render("", {})

    assert exc_info.value.error_type == "TEMPLATE_EMPTY"


def test_render_raises_when_template_contains_only_spaces() -> None:
    engine = TemplateEngine()

    with pytest.raises(TemplateRenderError) as exc_info:
        engine.render("   ", {})

    assert exc_info.value.error_type == "TEMPLATE_EMPTY"


def test_render_raises_when_context_is_not_dict() -> None:
    engine = TemplateEngine()

    with pytest.raises(TemplateRenderError) as exc_info:
        engine.render(
            template="Project: {{PROJECT_NAME}}",
            context=["PROJECT_NAME", "SpecFlow"],  # type: ignore[arg-type]
        )

    assert exc_info.value.error_type == "INVALID_CONTEXT"


@pytest.mark.parametrize(
    "invalid_variable",
    [
        "{{project_name}}",
        "{{ProjectName}}",
        "{{PROJECT NAME}}",
        "{{1_PROJECT}}",
        "{{プロジェクト名}}",
    ],
)
def test_render_raises_when_variable_name_is_invalid(
    invalid_variable: str,
) -> None:
    engine = TemplateEngine()

    with pytest.raises(TemplateRenderError) as exc_info:
        engine.render(
            template=invalid_variable,
            context={},
        )

    assert exc_info.value.error_type == "INVALID_VARIABLE_NAME"