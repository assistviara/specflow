from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from core.document_loader import load_text_file
from core.prompt_builder import PromptBuilder, PromptResult


class DocumentLoaderProtocol(Protocol):
    """Plan Prompt Generatorが必要とする文書読込契約。"""

    def load(self, path: Path) -> str:
        """指定された文書を読み込み、文字列として返す。"""
        ...


class PromptBuilderProtocol(Protocol):
    """Plan Prompt Generatorが必要とするPrompt Builder契約。"""

    def build(
        self,
        template: str,
        context: dict[str, object],
    ) -> PromptResult:
        """TemplateとContextからPromptResultを生成する。"""
        ...


class DocumentLoaderAdapter:
    """既存のDocument LoaderをProtocolへ適合させるAdapter。"""

    def load(self, path: Path) -> str:
        """既存のload_text_fileへ文書読込を委譲する。"""
        return load_text_file(path)


class PlanPromptGenerator:
    """Implementation Plan生成用Promptを構築する。"""

    def __init__(
        self,
        document_loader: DocumentLoaderProtocol | None = None,
        prompt_builder: PromptBuilderProtocol | None = None,
    ) -> None:
        self._document_loader = (
            document_loader or DocumentLoaderAdapter()
        )
        self._prompt_builder = prompt_builder or PromptBuilder()

    def generate(
        self,
        *,
        constitution_path: Path,
        principles_path: Path,
        specification_path: Path,
        decisions_path: Path,
        implementation_plan_template_path: Path,
        project_metadata: dict[str, Any],
        template_path: Path,
    ) -> PromptResult:
        constitution = self._document_loader.load(
            constitution_path
        )
        principles = self._document_loader.load(
            principles_path
        )
        specification = self._document_loader.load(
            specification_path
        )
        decisions = self._document_loader.load(
            decisions_path
        )
        implementation_plan_template = self._document_loader.load(
            implementation_plan_template_path
        )
        template = self._document_loader.load(
            template_path
        )

        context: dict[str, object] = {
            "CONSTITUTION": constitution,
            "PRINCIPLES": principles,
            "SPECIFICATION": specification,
            "DECISIONS": decisions,
            "PROJECT_NAME": project_metadata["project_name"],
            "TARGET_PATH": project_metadata["target_path"],
            "PROJECT_DESCRIPTION": project_metadata[
                "project_description"
            ],
            "PROJECT_VERSION": project_metadata["project_version"],
            "IMPLEMENTATION_PLAN_TEMPLATE": (
                implementation_plan_template
            ),
        }

        return self._prompt_builder.build(
            template=template,
            context=context,
        )