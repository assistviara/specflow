from pathlib import Path

import pytest

from core.document_loader import (
    DocumentLoadError,
    load_common_documents,
    load_json_file,
    load_plan_prompt_template,
    load_project_documents,
    load_text_file,
)


BASE_DIR = Path(__file__).resolve().parents[1]


def test_load_text_file_reads_utf8_text(tmp_path: Path) -> None:
    test_file = tmp_path / "sample.md"
    test_file.write_text("日本語テスト", encoding="utf-8")

    result = load_text_file(test_file)

    assert result == "日本語テスト"


def test_load_text_file_raises_when_file_not_found(tmp_path: Path) -> None:
    missing_file = tmp_path / "missing.md"

    with pytest.raises(DocumentLoadError) as exc_info:
        load_text_file(missing_file)

    assert exc_info.value.error_type == "FILE_NOT_FOUND"


def test_load_text_file_raises_when_file_is_empty(tmp_path: Path) -> None:
    empty_file = tmp_path / "empty.md"
    empty_file.write_text("", encoding="utf-8")

    with pytest.raises(DocumentLoadError) as exc_info:
        load_text_file(empty_file)

    assert exc_info.value.error_type == "EMPTY_FILE"


def test_load_json_file_reads_object(tmp_path: Path) -> None:
    json_file = tmp_path / "project.json"
    json_file.write_text(
        '{"project_name": "SpecFlow"}',
        encoding="utf-8",
    )

    result = load_json_file(json_file)

    assert result["project_name"] == "SpecFlow"


def test_load_json_file_raises_when_json_is_invalid(tmp_path: Path) -> None:
    json_file = tmp_path / "invalid.json"
    json_file.write_text('{"project_name": }', encoding="utf-8")

    with pytest.raises(DocumentLoadError) as exc_info:
        load_json_file(json_file)

    assert exc_info.value.error_type == "INVALID_JSON"


def test_load_common_documents() -> None:
    result = load_common_documents(BASE_DIR)

    assert "constitution" in result
    assert "principles" in result
    assert result["constitution"].strip()
    assert result["principles"].strip()


def test_load_project_documents() -> None:
    result = load_project_documents(BASE_DIR, "specflow")

    assert "specification" in result
    assert "decisions" in result
    assert "project" in result
    assert result["project"]["project_name"] == "SpecFlow"


def test_load_plan_prompt_template() -> None:
    result = load_plan_prompt_template(BASE_DIR)

    assert "# Plan Prompt Template" in result