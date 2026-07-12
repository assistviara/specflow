from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class DocumentLoadError(Exception):
    """正式文書の読み込み失敗を表す例外。"""

    def __init__(
        self,
        path: Path,
        error_type: str,
        guidance: str,
    ) -> None:
        self.path = path
        self.error_type = error_type
        self.guidance = guidance

        message = (
            f"文書の読み込みに失敗しました。\n"
            f"対象ファイル: {path}\n"
            f"エラー種別: {error_type}\n"
            f"確認事項: {guidance}"
        )
        super().__init__(message)


def load_text_file(path: str | Path) -> str:
    """
    UTF-8のテキストファイルを読み込んで返す。

    Raises:
        DocumentLoadError:
            ファイル不存在、ディレクトリ指定、空ファイル、
            UTF-8読込失敗、その他のI/Oエラー。
    """
    file_path = Path(path)

    if not file_path.exists():
        raise DocumentLoadError(
            path=file_path,
            error_type="FILE_NOT_FOUND",
            guidance="ファイルの保存場所とファイル名を確認してください。",
        )

    if not file_path.is_file():
        raise DocumentLoadError(
            path=file_path,
            error_type="NOT_A_FILE",
            guidance="ディレクトリではなく、ファイルを指定してください。",
        )

    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise DocumentLoadError(
            path=file_path,
            error_type="INVALID_ENCODING",
            guidance="ファイルがUTF-8で保存されているか確認してください。",
        ) from exc
    except OSError as exc:
        raise DocumentLoadError(
            path=file_path,
            error_type="IO_ERROR",
            guidance="ファイルの権限、使用中かどうか、保存場所を確認してください。",
        ) from exc

    if not content.strip():
        raise DocumentLoadError(
            path=file_path,
            error_type="EMPTY_FILE",
            guidance="ファイルに内容を記述して保存してください。",
        )

    return content


def load_json_file(path: str | Path) -> dict[str, Any]:
    """
    UTF-8のJSONファイルを読み込み、辞書として返す。

    Raises:
        DocumentLoadError:
            ファイル読込失敗、JSON形式不正、JSONの最上位が辞書でない場合。
    """
    file_path = Path(path)
    content = load_text_file(file_path)

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise DocumentLoadError(
            path=file_path,
            error_type="INVALID_JSON",
            guidance=(
                f"JSON形式を確認してください。"
                f" 行: {exc.lineno}, 列: {exc.colno}"
            ),
        ) from exc

    if not isinstance(data, dict):
        raise DocumentLoadError(
            path=file_path,
            error_type="INVALID_JSON_ROOT",
            guidance="JSONの最上位はオブジェクト形式にしてください。",
        )

    return data


def load_common_documents(base_dir: str | Path) -> dict[str, str]:
    """
    SpecFlow全体で共通利用する正式文書を読み込む。
    """
    base_path = Path(base_dir)

    return {
        "constitution": load_text_file(
            base_path / "constitution" / "constitution.md"
        ),
        "principles": load_text_file(
            base_path / "constitution" / "principles.md"
        ),
    }


def load_project_documents(
    base_dir: str | Path,
    project_name: str,
) -> dict[str, Any]:
    """
    指定プロジェクト固有の正式文書とメタデータを読み込む。
    """
    base_path = Path(base_dir)
    project_dir = base_path / "projects" / project_name

    return {
        "specification": load_text_file(
            project_dir / "docs" / "specification.md"
        ),
        "decisions": load_text_file(
            project_dir / "docs" / "decisions.md"
        ),
        "project": load_json_file(
            project_dir / "project.json"
        ),
    }


def load_plan_prompt_template(base_dir: str | Path) -> str:
    """
    Plan生成用Prompt Templateを読み込む。
    """
    base_path = Path(base_dir)

    return load_text_file(
        base_path
        / "prompt_templates"
        / "plan_prompt_template.md"
    )