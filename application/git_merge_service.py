"""Phase 6 Git observations, execution and separate result verification."""
from dataclasses import dataclass
from typing import Protocol

from application.repository_state_provider import RepositoryState


@dataclass(frozen=True)
class GitMergeResult:
    repository: str
    source_branch: str
    target_branch: str
    approved_commit: str
    pre_commit: str
    post_commit: str | None = None
    operation: str = 'merge'
    command_started: bool = False
    returncode: int | None = None
    stdout: str = ''
    stderr: str = ''
    conflicts: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    repository_state: RepositoryState | None = None

    @property
    def command_success(self) -> bool:
        return self.command_started and self.returncode == 0


@dataclass(frozen=True)
class GitMergeVerification:
    repository_state: RepositoryState | None = None
    current_head: str | None = None
    target_head: str | None = None
    source_head: str | None = None
    pending_operations: tuple[str, ...] | None = None
    integrated: bool = False
    errors: tuple[str, ...] = ()

    expected_tree: str | None = None
    actual_tree: str | None = None
    content_matched: bool = False
    approved_content_retained: bool = False

    @property
    def verified(self) -> bool:
        return (self.integrated and not self.errors and self.content_matched
                and self.approved_content_retained and bool(self.expected_tree)
                and self.expected_tree == self.actual_tree)


class GitMergeService(Protocol):
    def get_state(self, base_commit: str) -> RepositoryState:
        ...

    def get_current_head(self) -> str:
        ...

    def get_branch_head(self, branch: str) -> str:
        ...

    def get_pending_operations(self) -> tuple[str, ...]:
        ...

    def merge(self, source_branch: str, approved_commit: str, target_commit: str) -> GitMergeResult:
        ...

    def verify_merge(self, result: GitMergeResult, *, base_commit: str) -> GitMergeVerification:
        ...
