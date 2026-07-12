from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


# STL Version 1.0で有効な変数名
VALID_VARIABLE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")

# 二重波括弧の中身を抽出するためのパターン
TEMPLATE_VARIABLE_PATTERN = re.compile(r"{{\s*([^{}]+?)\s*}}")


class TemplateRenderError(Exception):
    """Templateの検証または展開に失敗したことを表す例外。"""

    def __init__(
        self,
        error_type: str,
        cause: str,
        guidance: str,
    ) -> None:
        self.error_type = error_type
        self.cause = cause
        self.guidance = guidance

        message = (
            "Templateの展開に失敗しました。\n"
            f"エラー種別: {error_type}\n"
            f"原因: {cause}\n"
            f"確認事項: {guidance}"
        )
        super().__init__(message)


@dataclass(frozen=True)
class RenderResult:
    """Templateの展開結果を保持する。"""

    content: str
    undefined_variables: list[str]
    unused_context: list[str]
    warnings: list[str]


class TemplateEngine:
    """STL Version 1.0に従ってTemplateを展開するEngine。"""

    def render(
        self,
        template: str,
        context: dict[str, object],
    ) -> RenderResult:
        """
        TemplateをContextで展開する。

        未定義変数や値がNoneの変数は推測せず、
        元の変数記法を残したまま警告を返す。
        """
        self._validate_template(template)
        self._validate_context(context)

        variables = self._extract_variables(template)
        rendered_content = template

        undefined_variables: list[str] = []
        none_variables: list[str] = []
        used_context_keys: set[str] = set()

        for variable in variables:
            placeholder_pattern = re.compile(
                r"{{\s*" + re.escape(variable) + r"\s*}}"
            )

            if variable not in context:
                undefined_variables.append(variable)
                continue

            used_context_keys.add(variable)
            value = context[variable]

            if value is None:
                none_variables.append(variable)
                continue

            rendered_content = placeholder_pattern.sub(
                lambda _: str(value),
                rendered_content,
            )

        unused_context = sorted(
            set(context.keys()) - used_context_keys
        )

        warnings = self._build_warnings(
            undefined_variables=undefined_variables,
            none_variables=none_variables,
            unused_context=unused_context,
        )

        return RenderResult(
            content=rendered_content,
            undefined_variables=sorted(undefined_variables),
            unused_context=unused_context,
            warnings=warnings,
        )

    def _validate_template(self, template: str) -> None:
        """Templateの型、空文字、変数名を検証する。"""
        if not isinstance(template, str):
            raise TemplateRenderError(
                error_type="INVALID_TEMPLATE",
                cause="Templateが文字列ではありません。",
                guidance="Templateには文字列を指定してください。",
            )

        if not template.strip():
            raise TemplateRenderError(
                error_type="TEMPLATE_EMPTY",
                cause="Templateが空です。",
                guidance="Templateに内容を記述してください。",
            )

        raw_variables = TEMPLATE_VARIABLE_PATTERN.findall(template)

        for raw_variable in raw_variables:
            variable = raw_variable.strip()

            if not VALID_VARIABLE_PATTERN.fullmatch(variable):
                raise TemplateRenderError(
                    error_type="INVALID_VARIABLE_NAME",
                    cause=f"無効な変数名です: {raw_variable}",
                    guidance=(
                        "変数名は英大文字で始め、"
                        "英大文字・数字・アンダースコアのみを使用してください。"
                    ),
                )

    def _validate_context(self, context: object) -> None:
        """Contextが辞書形式であることを確認する。"""
        if not isinstance(context, dict):
            raise TemplateRenderError(
                error_type="INVALID_CONTEXT",
                cause="Contextが辞書形式ではありません。",
                guidance="Contextにはdictを指定してください。",
            )

    def _extract_variables(self, template: str) -> list[str]:
        """Template内の変数を出現順で重複なく抽出する。"""
        extracted = TEMPLATE_VARIABLE_PATTERN.findall(template)

        variables: list[str] = []
        seen: set[str] = set()

        for raw_variable in extracted:
            variable = raw_variable.strip()

            if variable not in seen:
                seen.add(variable)
                variables.append(variable)

        return variables

    def _build_warnings(
        self,
        undefined_variables: list[str],
        none_variables: list[str],
        unused_context: list[str],
    ) -> list[str]:
        """展開結果に付随する警告文を生成する。"""
        warnings: list[str] = []

        for variable in sorted(undefined_variables):
            warnings.append(
                f"未定義変数です: {variable}"
            )

        for variable in sorted(none_variables):
            warnings.append(
                f"Contextの値がNoneです: {variable}"
            )

        for key in unused_context:
            warnings.append(
                f"使用されなかったContextです: {key}"
            )

        return warnings