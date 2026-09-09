from __future__ import annotations

from pathlib import Path
from typing import Protocol

from core.document_loader import load_text_file
from core.prompt_builder import PromptBuilder, PromptResult


class DocumentLoaderProtocol(Protocol):
    """Codex Prompt Generatorが必要とする文書読込契約。"""

    def load(self, path: Path) -> str:
        ...


class PromptBuilderProtocol(Protocol):
    """Codex Prompt Generatorが必要とするPrompt Builder契約。"""

    def build(
        self,
        template: str,
        context: dict[str, object],
    ) -> PromptResult:
        ...


class DocumentLoaderAdapter:
    """既存Document LoaderをProtocolへ適合させるAdapter。"""

    def load(self, path: Path) -> str:
        return load_text_file(path)


class CodexPromptGenerator:
    """Codex Implementation Prompt生成用Promptを構築する。"""

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
        specification_path: Path,
        implementation_plan_path: Path,
        implementation_target_path: Path,
        tdd_rules: str,
        completion_conditions: str,
        stop_conditions: str,
        execution_result_reporting_requirements: str,
        template_path: Path,
    ) -> PromptResult:
        specification = self._document_loader.load(
            specification_path
        )
        implementation_plan = self._document_loader.load(
            implementation_plan_path
        )
        template = self._document_loader.load(
            template_path
        )

        context: dict[str, object] = {
            "SPECIFICATION": specification,
            "IMPLEMENTATION_PLAN": implementation_plan,
            "IMPLEMENTATION_TARGET_PATH": str(
                implementation_target_path
            ),
            "TDD_RULES": tdd_rules,
            "COMPLETION_CONDITIONS": completion_conditions,
            "STOP_CONDITIONS": stop_conditions,
            "EXECUTION_RESULT_REPORTING_REQUIREMENTS": (
                execution_result_reporting_requirements
            ),
        }

        return self._prompt_builder.build(
            template=template,
            context=context,
        )
