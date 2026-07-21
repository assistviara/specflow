from pathlib import Path
import pytest

from core.document_loader import DocumentLoadError
from core.plan_prompt_generator import PlanPromptGenerator
from core.prompt_builder import PromptResult


class FakeDocumentLoader:
    def __init__(self) -> None:
        self.loaded_paths: list[Path] = []

    def load(self, path: Path) -> str:
        self.loaded_paths.append(path)
        return f"CONTENT:{path.name}"


class FakePromptBuilder:
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
            content="PROMPT",
            undefined_variables=[],
            unused_context=[],
            warnings=[],
        )

class FailingDocumentLoader:
    def load(self, path: Path) -> str:
        raise DocumentLoadError(
            path=path,
            error_type="TEST_ERROR",
            guidance="テスト用のエラーです。",
        )
    
class FailingPromptBuilder:
    def build(
        self,
        template: str,
        context: dict[str, object],
    ) -> PromptResult:
        raise RuntimeError("PromptBuilder failed")

def test_generate_returns_prompt_result() -> None:
    generator = PlanPromptGenerator(
        document_loader=FakeDocumentLoader(),
        prompt_builder=FakePromptBuilder(),
    )

    result = generator.generate(
        constitution_path=Path("constitution.md"),
        principles_path=Path("principles.md"),
        specification_path=Path("specification.md"),
        decisions_path=Path("decisions.md"),
        implementation_plan_template_path=Path(
            "implementation_plan_template.md"
        ),
        project_metadata={
            "project_name": "SpecFlow",
            "target_path": "specflow_starter/",
            "project_description": "仕様書中心のAI開発支援システム",
            "project_version": "0.2.0",
        },
        template_path=Path("plan_prompt_template.md"),
    )

    assert isinstance(result, PromptResult)
    assert result.content == "PROMPT"
    assert result.is_ready is True

def test_generate_loads_all_required_documents() -> None:
    document_loader = FakeDocumentLoader()

    generator = PlanPromptGenerator(
        document_loader=document_loader,
        prompt_builder=FakePromptBuilder(),
    )

    generator.generate(
        constitution_path=Path("constitution.md"),
        principles_path=Path("principles.md"),
        specification_path=Path("specification.md"),
        decisions_path=Path("decisions.md"),
        implementation_plan_template_path=Path(
            "implementation_plan_template.md"
        ),
        project_metadata={
            "project_name": "SpecFlow",
            "target_path": "specflow_starter/",
            "project_description": "仕様書中心のAI開発支援システム",
            "project_version": "0.2.0",
        },
        template_path=Path("plan_prompt_template.md"),
    )

    assert document_loader.loaded_paths == [
        Path("constitution.md"),
        Path("principles.md"),
        Path("specification.md"),
        Path("decisions.md"),
        Path("implementation_plan_template.md"),
        Path("plan_prompt_template.md"),
    ]

def test_generate_builds_expected_context() -> None:
    prompt_builder = FakePromptBuilder()

    generator = PlanPromptGenerator(
        document_loader=FakeDocumentLoader(),
        prompt_builder=prompt_builder,
    )

    generator.generate(
        constitution_path=Path("constitution.md"),
        principles_path=Path("principles.md"),
        specification_path=Path("specification.md"),
        decisions_path=Path("decisions.md"),
        implementation_plan_template_path=Path(
            "implementation_plan_template.md"
        ),
        project_metadata={
            "project_name": "SpecFlow",
            "target_path": "specflow_starter/",
            "project_description": "仕様書中心のAI開発支援システム",
            "project_version": "0.2.0",
        },
        template_path=Path("plan_prompt_template.md"),
    )

    assert prompt_builder.template == "CONTENT:plan_prompt_template.md"
    assert prompt_builder.context is not None

    assert prompt_builder.context["CONSTITUTION"] == (
        "CONTENT:constitution.md"
    )

    assert prompt_builder.context["PRINCIPLES"] == (
        "CONTENT:principles.md"
    )

    assert prompt_builder.context["SPECIFICATION"] == (
        "CONTENT:specification.md"
    )

    assert prompt_builder.context["DECISIONS"] == (
        "CONTENT:decisions.md"
    )

    assert prompt_builder.context["PROJECT_NAME"] == "SpecFlow"

    assert prompt_builder.context["TARGET_PATH"] == (
        "specflow_starter/"
    )

    assert prompt_builder.context["PROJECT_DESCRIPTION"] == (
        "仕様書中心のAI開発支援システム"
    )

    assert prompt_builder.context["PROJECT_VERSION"] == "0.2.0"

    assert prompt_builder.context[
        "IMPLEMENTATION_PLAN_TEMPLATE"
    ] == "CONTENT:implementation_plan_template.md"

    

def test_generate_propagates_document_loader_error() -> None:
    generator = PlanPromptGenerator(
        document_loader=FailingDocumentLoader(),
        prompt_builder=FakePromptBuilder(),
    )

    with pytest.raises(DocumentLoadError) as exc_info:
        generator.generate(
            constitution_path=Path("constitution.md"),
            principles_path=Path("principles.md"),
            specification_path=Path("specification.md"),
            decisions_path=Path("decisions.md"),
            project_metadata={
                "project_name": "SpecFlow",
                "target_path": "specflow_starter/",
                "project_description": "仕様書中心のAI開発支援システム",
                "project_version": "0.2.0",
            },
            template_path=Path("plan_prompt_template.md"),
        )

    assert exc_info.value.error_type == "TEST_ERROR"
    assert exc_info.value.path == Path("constitution.md")

def test_generate_propagates_document_loader_error() -> None:
    generator = PlanPromptGenerator(
        document_loader=FailingDocumentLoader(),
        prompt_builder=FakePromptBuilder(),
    )

    with pytest.raises(DocumentLoadError) as exc_info:
        generator.generate(
            constitution_path=Path("constitution.md"),
            principles_path=Path("principles.md"),
            specification_path=Path("specification.md"),
            decisions_path=Path("decisions.md"),
            implementation_plan_template_path=Path(
                "implementation_plan_template.md"
            ),
            project_metadata={
                "project_name": "SpecFlow",
                "target_path": "specflow_starter/",
                "project_description": "仕様書中心のAI開発支援システム",
                "project_version": "0.2.0",
            },
            template_path=Path("plan_prompt_template.md"),
        )

    assert exc_info.value.error_type == "TEST_ERROR"
    assert exc_info.value.path == Path("constitution.md")

def test_generate_propagates_prompt_builder_error() -> None:
    generator = PlanPromptGenerator(
        document_loader=FakeDocumentLoader(),
        prompt_builder=FailingPromptBuilder(),
    )

    with pytest.raises(
        RuntimeError,
        match="PromptBuilder failed",
    ):
        generator.generate(
            constitution_path=Path("constitution.md"),
            principles_path=Path("principles.md"),
            specification_path=Path("specification.md"),
            decisions_path=Path("decisions.md"),
            implementation_plan_template_path=Path(
                "implementation_plan_template.md"
            ),
            project_metadata={
                "project_name": "SpecFlow",
                "target_path": "specflow_starter/",
                "project_description": "仕様書中心のAI開発支援システム",
                "project_version": "0.2.0",
            },
            template_path=Path("plan_prompt_template.md"),
        )