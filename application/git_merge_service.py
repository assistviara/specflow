"""Only the read capabilities required by Final Approval Entry are defined here."""
from typing import Protocol

from application.repository_state_provider import RepositoryState


class GitMergeService(Protocol):
    def get_state(self, base_commit: str) -> RepositoryState:
        ...

    def get_current_head(self) -> str:
        ...
