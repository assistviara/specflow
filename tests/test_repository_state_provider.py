from dataclasses import FrozenInstanceError
from typing import Protocol

import pytest

from application.repository_state_provider import (
    RepositoryState,
    RepositoryStateProvider,
)


def test_repository_state_is_frozen_dataclass() -> None:
    state = RepositoryState(
        branch="developer",
        base_commit="abc123",
        git_status=" M application/example.py",
        git_diff="diff --git a/application/example.py",
        created_files=("application/new.py",),
        modified_files=("application/example.py",),
        deleted_files=("application/old.py",),
    )

    assert state.branch == "developer"
    assert state.base_commit == "abc123"
    assert state.git_status == " M application/example.py"
    assert state.git_diff == (
        "diff --git a/application/example.py"
    )
    assert state.created_files == (
        "application/new.py",
    )
    assert state.modified_files == (
        "application/example.py",
    )
    assert state.deleted_files == (
        "application/old.py",
    )

    with pytest.raises(FrozenInstanceError):
        state.branch = "main"


def test_repository_state_accepts_empty_change_groups() -> None:
    state = RepositoryState(
        branch="developer",
        base_commit="abc123",
        git_status="",
        git_diff="",
        created_files=(),
        modified_files=(),
        deleted_files=(),
    )

    assert state.git_status == ""
    assert state.git_diff == ""
    assert state.created_files == ()
    assert state.modified_files == ()
    assert state.deleted_files == ()


def test_repository_state_provider_is_protocol() -> None:
    assert issubclass(
        RepositoryStateProvider,
        Protocol,
    )


def test_repository_state_provider_exposes_get_state() -> None:
    assert "get_state" in RepositoryStateProvider.__dict__


def test_repository_state_preserves_unavailable_evidence() -> None:
    state = RepositoryState(
        branch="developer",
        base_commit="abc123",
        git_status="",
        git_diff="",
        created_files=(),
        modified_files=(),
        deleted_files=(),
        unavailable_evidence=("git_diff",),
    )

    assert state.git_diff == ""
    assert state.unavailable_evidence == ("git_diff",)
