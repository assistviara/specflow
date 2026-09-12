from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from application.implementation_evidence import EvidenceChanges


def test_evidence_changes_is_frozen_dataclass() -> None:
    changes = EvidenceChanges(
        created_files=(
            "application/new_file.py",
        ),
        modified_files=(
            "application/existing_file.py",
        ),
        deleted_files=(
            "application/old_file.py",
        ),
        git_diff_path=Path(
            "evidence/implementation_evidence.diff"
        ),
        change_summary="Implementation Evidence基盤を追加",
    )

    assert changes.created_files == (
        "application/new_file.py",
    )
    assert changes.modified_files == (
        "application/existing_file.py",
    )
    assert changes.deleted_files == (
        "application/old_file.py",
    )
    assert changes.git_diff_path == Path(
        "evidence/implementation_evidence.diff"
    )
    assert (
        changes.change_summary
        == "Implementation Evidence基盤を追加"
    )

    with pytest.raises(FrozenInstanceError):
        changes.change_summary = "changed"


def test_evidence_changes_allows_missing_git_diff() -> None:
    changes = EvidenceChanges(
        created_files=(),
        modified_files=(),
        deleted_files=(),
        git_diff_path=None,
        change_summary="",
    )

    assert changes.created_files == ()
    assert changes.modified_files == ()
    assert changes.deleted_files == ()
    assert changes.git_diff_path is None
    assert changes.change_summary == ""


def test_evidence_changes_allows_none_change_summary() -> None:
    from typing import get_type_hints

    hints = get_type_hints(EvidenceChanges)

    assert hints["change_summary"] == str | None

    changes = EvidenceChanges(
        created_files=(),
        modified_files=(),
        deleted_files=(),
        git_diff_path=None,
        change_summary=None,
    )

    assert changes.change_summary is None
