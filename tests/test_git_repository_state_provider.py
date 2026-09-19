import subprocess
from pathlib import Path

import pytest

from infrastructure.git_repository_state_provider import (
    GitRepositoryStateProvider,
)


def run_git(
    working_directory: Path,
    *arguments: str,
) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=working_directory,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def make_clean_repository(tmp_path: Path) -> tuple[Path, str]:
    repository_path = tmp_path / "repository"
    repository_path.mkdir()

    run_git(repository_path, "init")
    run_git(
        repository_path,
        "config",
        "user.email",
        "test@example.com",
    )
    run_git(
        repository_path,
        "config",
        "user.name",
        "SpecFlow Test",
    )
    run_git(repository_path, "checkout", "-b", "developer")

    tracked_file = repository_path / "tracked.txt"
    tracked_file.write_text(
        "initial content\n",
        encoding="utf-8",
    )

    run_git(repository_path, "add", "tracked.txt")
    run_git(
        repository_path,
        "commit",
        "-m",
        "initial commit",
    )

    base_commit = run_git(
        repository_path,
        "rev-parse",
        "HEAD",
    )

    return repository_path, base_commit


def test_get_state_collects_clean_repository_state(
    tmp_path: Path,
) -> None:
    repository_path, base_commit = make_clean_repository(
        tmp_path
    )
    provider = GitRepositoryStateProvider(
        working_directory=repository_path
    )

    state = provider.get_state(base_commit)

    assert state.branch == "developer"
    assert state.base_commit == base_commit
    assert state.git_status == ""
    assert state.git_diff == ""
    assert state.created_files == ()
    assert state.modified_files == ()
    assert state.deleted_files == ()
    assert state.unavailable_evidence == ()



def test_get_state_classifies_tracked_file_changes(
    tmp_path: Path,
) -> None:
    repository_path = tmp_path / "repository"
    repository_path.mkdir()

    run_git(repository_path, "init")
    run_git(
        repository_path,
        "config",
        "user.email",
        "test@example.com",
    )
    run_git(
        repository_path,
        "config",
        "user.name",
        "SpecFlow Test",
    )
    run_git(repository_path, "checkout", "-b", "developer")

    modified_file = repository_path / "modified.txt"
    deleted_file = repository_path / "deleted.txt"

    modified_file.write_text(
        "before modification\n",
        encoding="utf-8",
    )
    deleted_file.write_text(
        "deleted later\n",
        encoding="utf-8",
    )

    run_git(repository_path, "add", ".")
    run_git(
        repository_path,
        "commit",
        "-m",
        "base commit",
    )

    base_commit = run_git(
        repository_path,
        "rev-parse",
        "HEAD",
    )

    modified_file.write_text(
        "after modification\n",
        encoding="utf-8",
    )
    deleted_file.unlink()

    created_file = repository_path / "created.txt"
    created_file.write_text(
        "created after base\n",
        encoding="utf-8",
    )

    run_git(repository_path, "add", "-A")

    provider = GitRepositoryStateProvider(
        working_directory=repository_path
    )

    state = provider.get_state(base_commit)

    assert state.created_files == ("created.txt",)
    assert state.modified_files == ("modified.txt",)
    assert state.deleted_files == ("deleted.txt",)
    assert state.git_status != ""
    assert state.git_diff != ""
    assert state.unavailable_evidence == ()



def test_get_state_represents_rename_as_delete_and_create(
    tmp_path: Path,
) -> None:
    repository_path, base_commit = make_clean_repository(
        tmp_path
    )

    run_git(
        repository_path,
        "mv",
        "tracked.txt",
        "renamed.txt",
    )

    provider = GitRepositoryStateProvider(
        working_directory=repository_path
    )

    state = provider.get_state(base_commit)

    assert state.created_files == ("renamed.txt",)
    assert state.modified_files == ()
    assert state.deleted_files == ("tracked.txt",)
    assert state.git_status != ""
    assert state.git_diff != ""
    assert state.unavailable_evidence == ()



def test_get_state_adds_untracked_files_to_created_files(
    tmp_path: Path,
) -> None:
    repository_path, base_commit = make_clean_repository(
        tmp_path
    )

    untracked_file = repository_path / "untracked.txt"
    untracked_file.write_text(
        "not added to Git\n",
        encoding="utf-8",
    )

    provider = GitRepositoryStateProvider(
        working_directory=repository_path
    )

    state = provider.get_state(base_commit)

    assert state.created_files == ("untracked.txt",)
    assert state.modified_files == ()
    assert state.deleted_files == ()
    assert "?? untracked.txt" in state.git_status
    assert state.git_diff == ""
    assert state.unavailable_evidence == ()



def test_get_state_preserves_untracked_path_with_spaces_and_non_ascii_characters(
    tmp_path: Path,
) -> None:
    repository_path, base_commit = make_clean_repository(
        tmp_path
    )

    relative_path = "日本語 file.txt"
    untracked_file = repository_path / relative_path
    untracked_file.write_text(
        "untracked content\n",
        encoding="utf-8",
    )

    provider = GitRepositoryStateProvider(
        working_directory=repository_path
    )

    state = provider.get_state(base_commit)

    assert state.created_files == (relative_path,)
    assert state.modified_files == ()
    assert state.deleted_files == ()
    assert relative_path in state.git_status
    assert state.git_diff == ""
    assert state.unavailable_evidence == ()



def test_get_state_marks_base_dependent_evidence_unavailable(
    tmp_path: Path,
) -> None:
    repository_path, _ = make_clean_repository(tmp_path)

    provider = GitRepositoryStateProvider(
        working_directory=repository_path
    )

    state = provider.get_state(
        "commit-that-does-not-exist"
    )

    assert state.branch == "developer"
    assert state.base_commit == ""
    assert state.git_status == ""
    assert state.git_diff == ""
    assert state.created_files == ()
    assert state.modified_files == ()
    assert state.deleted_files == ()
    assert state.unavailable_evidence == (
        "base_commit",
        "git_diff",
        "changed_files",
    )



def test_get_state_marks_only_branch_unavailable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repository_path, base_commit = make_clean_repository(
        tmp_path
    )
    provider = GitRepositoryStateProvider(
        working_directory=repository_path
    )
    original_run_git = provider._run_git

    def run_git_with_branch_failure(*arguments: str) -> str:
        if arguments == ("branch", "--show-current"):
            raise subprocess.CalledProcessError(
                returncode=128,
                cmd=["git", *arguments],
            )
        return original_run_git(*arguments)

    monkeypatch.setattr(
        provider,
        "_run_git",
        run_git_with_branch_failure,
    )

    state = provider.get_state(base_commit)

    assert state.branch == ""
    assert state.base_commit == base_commit
    assert state.git_status == ""
    assert state.git_diff == ""
    assert state.created_files == ()
    assert state.modified_files == ()
    assert state.deleted_files == ()
    assert state.unavailable_evidence == (
        "implementation_branch",
    )



def test_get_state_marks_only_git_status_unavailable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repository_path, base_commit = make_clean_repository(
        tmp_path
    )
    provider = GitRepositoryStateProvider(
        working_directory=repository_path
    )
    original_run_git = provider._run_git

    def run_git_with_status_failure(*arguments: str) -> str:
        if arguments[:2] == (
            "status",
            "--porcelain=v1",
        ):
            raise subprocess.CalledProcessError(
                returncode=128,
                cmd=["git", *arguments],
            )
        return original_run_git(*arguments)

    monkeypatch.setattr(
        provider,
        "_run_git",
        run_git_with_status_failure,
    )

    state = provider.get_state(base_commit)

    assert state.branch == "developer"
    assert state.base_commit == base_commit
    assert state.git_status == ""
    assert state.git_diff == ""
    assert state.created_files == ()
    assert state.modified_files == ()
    assert state.deleted_files == ()
    assert state.unavailable_evidence == (
        "git_status",
        "changed_files",
    )



def test_get_state_marks_only_git_diff_unavailable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repository_path, base_commit = make_clean_repository(
        tmp_path
    )
    provider = GitRepositoryStateProvider(
        working_directory=repository_path
    )
    original_run_git = provider._run_git

    def run_git_with_diff_failure(*arguments: str) -> str:
        if arguments[:2] == ("diff", "--binary"):
            raise subprocess.CalledProcessError(
                returncode=128,
                cmd=["git", *arguments],
            )
        return original_run_git(*arguments)

    monkeypatch.setattr(
        provider,
        "_run_git",
        run_git_with_diff_failure,
    )

    state = provider.get_state(base_commit)

    assert state.branch == "developer"
    assert state.base_commit == base_commit
    assert state.git_status == ""
    assert state.git_diff == ""
    assert state.created_files == ()
    assert state.modified_files == ()
    assert state.deleted_files == ()
    assert state.unavailable_evidence == (
        "git_diff",
    )



def test_get_state_preserves_untracked_files_when_changed_file_lookup_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repository_path, base_commit = make_clean_repository(
        tmp_path
    )

    tracked_file = repository_path / "tracked.txt"
    tracked_file.write_text(
        "modified content\n",
        encoding="utf-8",
    )

    untracked_file = repository_path / "untracked.txt"
    untracked_file.write_text(
        "untracked content\n",
        encoding="utf-8",
    )

    provider = GitRepositoryStateProvider(
        working_directory=repository_path
    )
    original_run_git = provider._run_git

    def run_git_with_name_status_failure(
        *arguments: str,
    ) -> str:
        if arguments[:2] == (
            "diff",
            "--name-status",
        ):
            raise subprocess.CalledProcessError(
                returncode=128,
                cmd=["git", *arguments],
            )
        return original_run_git(*arguments)

    monkeypatch.setattr(
        provider,
        "_run_git",
        run_git_with_name_status_failure,
    )

    state = provider.get_state(base_commit)

    assert state.branch == "developer"
    assert state.base_commit == base_commit
    assert state.git_status != ""
    assert state.git_diff != ""
    assert state.created_files == ("untracked.txt",)
    assert state.modified_files == ()
    assert state.deleted_files == ()
    assert state.unavailable_evidence == (
        "changed_files",
    )



def test_get_state_deduplicates_unavailable_evidence_markers(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repository_path, base_commit = make_clean_repository(
        tmp_path
    )
    provider = GitRepositoryStateProvider(
        working_directory=repository_path
    )
    original_run_git = provider._run_git

    def run_git_with_evidence_failures(
        *arguments: str,
    ) -> str:
        if arguments[:2] == (
            "status",
            "--porcelain=v1",
        ):
            raise subprocess.CalledProcessError(
                returncode=128,
                cmd=["git", *arguments],
            )
        if arguments[:2] == ("diff", "--binary"):
            raise subprocess.CalledProcessError(
                returncode=128,
                cmd=["git", *arguments],
            )
        if arguments[:2] == (
            "diff",
            "--name-status",
        ):
            raise subprocess.CalledProcessError(
                returncode=128,
                cmd=["git", *arguments],
            )
        return original_run_git(*arguments)

    monkeypatch.setattr(
        provider,
        "_run_git",
        run_git_with_evidence_failures,
    )

    state = provider.get_state(base_commit)

    assert state.branch == "developer"
    assert state.base_commit == base_commit
    assert state.git_status == ""
    assert state.git_diff == ""
    assert state.created_files == ()
    assert state.modified_files == ()
    assert state.deleted_files == ()
    assert state.unavailable_evidence == (
        "git_status",
        "changed_files",
        "git_diff",
    )



def test_get_state_propagates_unexpected_provider_failure(
    tmp_path: Path,
) -> None:
    missing_repository = tmp_path / "missing-repository"
    provider = GitRepositoryStateProvider(
        working_directory=missing_repository
    )

    with pytest.raises(OSError):
        provider.get_state("abc123")
