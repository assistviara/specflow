from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RepositoryState:
    branch: str
    base_commit: str
    git_status: str
    git_diff: str
    created_files: tuple[str, ...]
    modified_files: tuple[str, ...]
    deleted_files: tuple[str, ...]
    unavailable_evidence: tuple[str, ...] = ()


class RepositoryStateProvider(Protocol):
    def get_state(
        self,
        base_commit: str,
    ) -> RepositoryState:
        ...
