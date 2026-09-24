"""Read capabilities for Final Approval Entry and Merge Preconditions."""
from typing import Protocol

from application.repository_state_provider import RepositoryState


class GitMergeService(Protocol):
    def get_state(self, base_commit: str) -> RepositoryState:
        ...

    def get_current_head(self) -> str:
        ...

    def get_branch_head(self, branch: str) -> str:
        ...

    def get_pending_operations(self) -> tuple[str, ...]:
        ...
