from pathlib import Path
import subprocess

from application.implementation_preparation import PreparedImplementation
from infrastructure.git_cli_merge_service import GitCliMergeService


class GitImplementationPreparation:
    """Create one dedicated branch from the local developer commit."""

    def prepare(self, repository: Path, branch: str) -> PreparedImplementation:
        root = repository.resolve()

        def git(*args):
            return subprocess.run(['git', *args], cwd=root, check=True,
                                  capture_output=True, text=True, encoding='utf-8').stdout.strip()

        if Path(git('rev-parse', '--show-toplevel')).resolve() != root:
            raise ValueError('Working directory must identify the repository root.')
        if not branch or branch in ('developer', 'main') or branch.startswith('-'):
            raise ValueError('A dedicated implementation branch is required.')
        git('check-ref-format', '--branch', branch)
        # Reuse read-only repository/safety operations; never invoke Merge.
        repository_reader = GitCliMergeService(root)
        if repository_reader.get_pending_operations():
            raise ValueError('Repository has a pending Git operation.')
        base = repository_reader.get_branch_head('developer')
        observed = repository_reader.get_state(base)
        if observed.unavailable_evidence or observed.git_status:
            raise ValueError('Repository safety could not be established or working tree is dirty.')
        if git('branch', '--list', branch):
            raise ValueError('Implementation branch already exists; it will not be reset.')
        git('checkout', '-b', branch, base)
        if git('branch', '--show-current') != branch or repository_reader.get_current_head() != base:
            raise ValueError('Prepared branch / base verification failed; no rollback was attempted.')
        return PreparedImplementation(root, 'developer', base, branch)
