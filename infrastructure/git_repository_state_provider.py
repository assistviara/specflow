import subprocess
from pathlib import Path

from application.repository_state_provider import (
    RepositoryState,
)


class GitRepositoryStateProvider:
    def __init__(
        self,
        working_directory: Path,
    ) -> None:
        self._working_directory = working_directory

    def get_state(
        self,
        base_commit: str,
    ) -> RepositoryState:
        unavailable_evidence: list[str] = []

        try:
            branch = self._run_git(
                "branch",
                "--show-current",
            ).strip()
        except subprocess.CalledProcessError:
            branch = ""
            unavailable_evidence.append(
                "implementation_branch"
            )

        try:
            raw_git_status = self._run_git(
                "status",
                "--porcelain=v1",
                "-z",
                "--untracked-files=all",
            )
            git_status = raw_git_status.rstrip(
                "\0"
            ).replace(
                "\0",
                "\n",
            )
        except subprocess.CalledProcessError:
            raw_git_status = ""
            git_status = ""
            unavailable_evidence.extend(
                (
                    "git_status",
                    "changed_files",
                )
            )

        try:
            resolved_base_commit = self._run_git(
                "rev-parse",
                "--verify",
                f"{base_commit}^{{commit}}",
            ).strip()
        except subprocess.CalledProcessError:
            return RepositoryState(
                branch=branch,
                base_commit="",
                git_status=git_status,
                git_diff="",
                created_files=(),
                modified_files=(),
                deleted_files=(),
                unavailable_evidence=self._deduplicate(
                    (
                        *unavailable_evidence,
                        "base_commit",
                        "git_diff",
                        "changed_files",
                    )
                ),
            )

        try:
            git_diff = self._run_git(
                "diff",
                "--binary",
                "--find-renames",
                resolved_base_commit,
                "--",
            )
        except subprocess.CalledProcessError:
            git_diff = ""
            unavailable_evidence.append("git_diff")

        try:
            name_status = self._run_git(
                "diff",
                "--name-status",
                "--find-renames",
                resolved_base_commit,
                "--",
            )
        except subprocess.CalledProcessError:
            name_status = ""
            unavailable_evidence.append("changed_files")

        (
            created_files,
            modified_files,
            deleted_files,
        ) = self._classify_changed_files(name_status)

        untracked_files = self._collect_untracked_files(
            raw_git_status
        )
        created_files = self._deduplicate(
            (*created_files, *untracked_files)
        )

        return RepositoryState(
            branch=branch,
            base_commit=resolved_base_commit,
            git_status=git_status,
            git_diff=git_diff,
            created_files=created_files,
            modified_files=modified_files,
            deleted_files=deleted_files,
            unavailable_evidence=self._deduplicate(
                tuple(unavailable_evidence)
            ),
        )

    @staticmethod
    def _classify_changed_files(
        name_status: str,
    ) -> tuple[
        tuple[str, ...],
        tuple[str, ...],
        tuple[str, ...],
    ]:
        created_files: list[str] = []
        modified_files: list[str] = []
        deleted_files: list[str] = []

        for line in name_status.splitlines():
            if not line:
                continue

            parts = line.split("\t")
            status = parts[0]

            if status == "A" and len(parts) == 2:
                created_files.append(parts[1])
            elif status == "M" and len(parts) == 2:
                modified_files.append(parts[1])
            elif status == "D" and len(parts) == 2:
                deleted_files.append(parts[1])
            elif status.startswith("R") and len(parts) == 3:
                deleted_files.append(parts[1])
                created_files.append(parts[2])

        return (
            tuple(created_files),
            tuple(modified_files),
            tuple(deleted_files),
        )

    @staticmethod
    def _collect_untracked_files(
        git_status: str,
    ) -> tuple[str, ...]:
        return tuple(
            entry[3:]
            for entry in git_status.split("\0")
            if entry.startswith("?? ")
        )

    @staticmethod
    def _deduplicate(
        values: tuple[str, ...],
    ) -> tuple[str, ...]:
        return tuple(dict.fromkeys(values))

    def _run_git(
        self,
        *arguments: str,
    ) -> str:
        result = subprocess.run(
            ["git", *arguments],
            cwd=self._working_directory,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        return result.stdout
