"""Read-only Phase 6 entry capabilities; no merge or retry is implemented."""
from pathlib import Path
import subprocess

from application.repository_state_provider import RepositoryState
from infrastructure.git_repository_state_provider import GitRepositoryStateProvider


class GitCliMergeService:
    def __init__(self, working_directory: Path) -> None:
        self._working_directory = working_directory
        self._repository = GitRepositoryStateProvider(working_directory)

    def get_state(self, base_commit: str) -> RepositoryState:
        return self._repository.get_state(base_commit)

    def get_current_head(self) -> str:
        result = subprocess.run(
            ['git', 'rev-parse', '--verify', 'HEAD^{commit}'],
            cwd=self._working_directory, check=True, capture_output=True,
            text=True, encoding='utf-8',
        )
        return result.stdout.strip()
