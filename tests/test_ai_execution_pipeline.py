from pathlib import Path

from core.ai.dummy_runner import DummyAIRunner
from core.ai.prompt_adapter import PromptAdapter
from core.plan_prompt_generator import PlanPromptGenerator


def write_text_file(
    directory: Path,
    filename: str,
    content: str,
) -> Path:
    """テスト用のUTF-8テキストファイルを作成する。"""
    path = directory / filename
    path.write_text(content, encoding="utf-8")
    return path


def test_plan_prompt_can_be_executed_by_dummy_ai(
    tmp_path: Path,
) -> None:
    """Plan Prompt生成からDummy AI実行までの一連の流れを確認する。"""

    constitution_path = write_text_file(
        tmp_path,
        "constitution.md",
        "# Constitution\n仕様書を優先する。",
    )

    principles_path = write_text_file(
        tmp_path,
        "principles.md",
        "# Principles\n人間が最終判断を行う。",
    )

    specification_path = write_text_file(
        tmp_path,
        "specification.md",
        "# Specification\nAI Runnerを実装する。",
    )

    decisions_path = write_text_file(
        tmp_path,
        "decisions.md",
        "# Decisions\nDummyAIRunnerを使用する。",
    )

    template_path = write_text_file(
        tmp_path,
        "plan_prompt_template.md",
        (
            "# Implementation Plan Request\n\n"
            "## Constitution\n"
            "{{CONSTITUTION}}\n\n"
            "## Principles\n"
            "{{PRINCIPLES}}\n\n"
            "## Specification\n"
            "{{SPECIFICATION}}\n\n"
            "## Decisions\n"
            "{{DECISIONS}}\n\n"
            "## Project Information\n"
            "- Project: {{PROJECT_NAME}}\n"
            "- Target: {{TARGET_PATH}}\n"
            "- Description: {{PROJECT_DESCRIPTION}}\n"
            "- Version: {{PROJECT_VERSION}}\n"
        ),
    )

    generator = PlanPromptGenerator()
    runner = DummyAIRunner()

    prompt_result = generator.generate(
        constitution_path=constitution_path,
        principles_path=principles_path,
        specification_path=specification_path,
        decisions_path=decisions_path,
        project_metadata={
            "project_name": "SpecFlow",
            "target_path": "specflow_starter/",
            "project_description": (
                "仕様書中心のAI開発支援システム"
            ),
            "project_version": "0.2.0",
        },
        template_path=template_path,
    )

    request = PromptAdapter.to_ai_request(prompt_result)
    response = runner.run(request)

    assert prompt_result.is_ready is True
    assert prompt_result.undefined_variables == []

    assert request.prompt == prompt_result.content

    assert response.success is True
    assert response.error_message is None
    assert request.prompt in response.content

    assert "仕様書を優先する。" in response.content
    assert "人間が最終判断を行う。" in response.content
    assert "AI Runnerを実装する。" in response.content
    assert "DummyAIRunnerを使用する。" in response.content

    assert "Project: SpecFlow" in response.content
    assert "Target: specflow_starter/" in response.content
    assert (
        "Description: 仕様書中心のAI開発支援システム"
        in response.content
    )
    assert "Version: 0.2.0" in response.content