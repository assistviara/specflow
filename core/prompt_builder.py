from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from core.template_engine import RenderResult, TemplateEngine


class TemplateEngineProtocol(Protocol):
    """Prompt Builderが利用するTemplate Engineの最小インターフェース。"""

    def render(
        self,
        template: str,
        context: dict[str, object],
    ) -> RenderResult:
        ...


@dataclass(frozen=True)
class PromptResult:
    """Prompt生成結果と検証情報を保持する。"""

    content: str
    undefined_variables: list[str]
    unused_context: list[str]
    warnings: list[str]

    @property
    def is_ready(self) -> bool:
        """未定義変数がなければ後続処理へ渡せる状態と判定する。"""
        return not self.undefined_variables


class PromptBuilder:
    """Template Engineを利用してPromptResultを生成する。"""

    def __init__(
        self,
        template_engine: TemplateEngineProtocol | None = None,
    ) -> None:
        self._template_engine = template_engine or TemplateEngine()

    def build(
        self,
        template: str,
        context: dict[str, object],
    ) -> PromptResult:
        """
        TemplateとContextをTemplate Engineへ渡し、
        RenderResultをPromptResultへ変換して返す。

        Template Engineの例外は握りつぶさず、そのまま伝播させる。
        """
        render_result = self._template_engine.render(
            template=template,
            context=context,
        )

        return PromptResult(
            content=render_result.content,
            undefined_variables=list(
                render_result.undefined_variables
            ),
            unused_context=list(
                render_result.unused_context
            ),
            warnings=list(render_result.warnings),
        )