"""Phase 6 Git operations; conflict resolution and retry are never automatic."""
from dataclasses import replace
from pathlib import Path
import subprocess

from application.repository_state_provider import RepositoryState
from application.git_merge_service import GitMergeResult, GitMergeVerification
from infrastructure.git_repository_state_provider import GitRepositoryStateProvider


class GitCliMergeService:
    def __init__(self, working_directory: Path) -> None:
        self._working_directory = working_directory.resolve()
        self._repository = GitRepositoryStateProvider(self._working_directory)

    def get_repository_identity(self) -> str:
        return str(self._working_directory)

    def get_state(self, base_commit: str) -> RepositoryState:
        return self._repository.get_state(base_commit)

    def get_current_head(self) -> str:
        result = subprocess.run(
            ['git', 'rev-parse', '--verify', 'HEAD^{commit}'],
            cwd=self._working_directory, check=True, capture_output=True,
            text=True, encoding='utf-8',
        )
        return result.stdout.strip()

    def get_branch_head(self, branch: str) -> str:
        result = subprocess.run(
            ['git', 'rev-parse', '--verify', f'refs/heads/{branch}^{{commit}}'],
            cwd=self._working_directory, check=True, capture_output=True,
            text=True, encoding='utf-8',
        )
        return result.stdout.strip()

    def get_pending_operations(self) -> tuple[str, ...]:
        pending = []
        # --git-path also handles linked worktrees without assuming .git is a directory.
        for name in ('MERGE_HEAD', 'CHERRY_PICK_HEAD', 'REVERT_HEAD',
                     'rebase-merge', 'rebase-apply', 'sequencer'):
            result = subprocess.run(
                ['git', 'rev-parse', '--git-path', name],
                cwd=self._working_directory, check=True, capture_output=True,
                text=True, encoding='utf-8',
            )
            path = Path(result.stdout.strip())
            if not path.is_absolute():
                path = self._working_directory / path
            if path.exists():
                pending.append(name)
        return tuple(pending)

    def merge(self, source_branch: str, approved_commit: str, target_commit: str) -> GitMergeResult:
        return self._execute_merge(source_branch, approved_commit, target_commit)

    def retry_merge(self, failed: GitMergeResult) -> GitMergeResult:
        if (failed.repository != self.get_repository_identity() or failed.operation != 'merge'
                or failed.target_branch != 'developer' or failed.command_success):
            raise ValueError('Same failed merge operation required')
        return self._execute_merge(failed.source_branch, failed.approved_commit, failed.pre_commit, retry=True)

    def _execute_merge(self, source_branch: str, approved_commit: str, target_commit: str,
                       *, retry: bool = False) -> GitMergeResult:
        result = GitMergeResult(str(self._working_directory), source_branch, 'developer',
            approved_commit, target_commit)
        try:
            state = self.get_state(target_commit)
            on_target = retry and state.branch == 'developer'
            if (state.unavailable_evidence or state.git_status
                    or state.branch not in ((source_branch, 'developer') if retry else (source_branch,))
                    or self.get_pending_operations()
                    or self.get_current_head() != (target_commit if on_target else approved_commit)
                    or self.get_branch_head(source_branch) != approved_commit
                    or self.get_branch_head('developer') != target_commit):
                raise ValueError('Repository changed before merge checkout')
            if not on_target:
                self._command('checkout', '--no-guess', 'developer')
            state = self.get_state(target_commit)
            if (state.unavailable_evidence or state.git_status or state.branch != 'developer'
                    or self.get_pending_operations() or self.get_current_head() != target_commit
                    or self.get_branch_head('developer') != target_commit
                    or self.get_branch_head(source_branch) != approved_commit):
                raise ValueError('Repository changed after merge checkout')
            # Pin the approved commit; disable stash and reuse of conflict
            # resolutions. Never repair a conflict or modify the source branch.
            options = self._content_options()
            result = replace(result, command_started=True)
            command = self._command(*options, '-c', 'branch.developer.mergeoptions=',
                '-c', 'rerere.enabled=false', 'merge', '--ff',
                '--no-squash', '--commit', '--no-edit', '--no-autostash', approved_commit, check=False)
            result = replace(result, returncode=command.returncode, stdout=command.stdout,
                stderr=command.stderr, warnings=(command.stderr,) if command.returncode == 0 and command.stderr else ())
            if command.returncode:
                result = replace(result, errors=(command.stderr or command.stdout or 'Git merge failed',))
        except Exception as exc:
            detail = f'{type(exc).__name__}: {exc}'
            stderr = getattr(exc, 'stderr', '') or ''
            stdout = getattr(exc, 'stdout', '') or ''
            result = replace(result, errors=(*result.errors, detail),
                stderr=result.stderr or stderr, stdout=result.stdout or stdout)
        # These observations are retained even for conflicts or failed commands.
        try:
            result = replace(result, post_commit=self.get_branch_head('developer'))
        except Exception as exc:
            result = replace(result, errors=(*result.errors, f'Post-merge HEAD unavailable: {exc}'))
        try:
            conflicts = self._command('diff', '--name-only', '--diff-filter=U', '-z').stdout
            result = replace(result, conflicts=tuple(p for p in conflicts.split('\0') if p))
        except Exception as exc:
            result = replace(result, errors=(*result.errors, f'Conflict information unavailable: {exc}'))
        try:
            state = self.get_state(target_commit)
            result = replace(result, repository_state=state)
            if state.unavailable_evidence:
                result = replace(result, errors=(*result.errors, f'Post-merge information missing: {state.unavailable_evidence}'))
        except Exception as exc:
            result = replace(result, errors=(*result.errors, f'Post-merge repository unavailable: {exc}'))
        return result

    def verify_merge(self, result: GitMergeResult, *, base_commit: str) -> GitMergeVerification:
        errors = []
        state = head = target = source = pending = None
        integrated = False
        expected_tree = actual_tree = None
        content_matched = retained_content = False
        if (not result.command_success or result.errors or result.conflicts
                or result.target_branch != 'developer' or not result.post_commit
                or result.repository != str(self._working_directory)):
            errors.append('Merge result does not identify a successful developer merge')
        try:
            state = self.get_state(result.pre_commit)
            if state.branch != 'developer' or state.unavailable_evidence or state.git_status:
                errors.append('Post-merge repository is not clean on developer')
        except Exception as exc:
            errors.append(f'Post-merge repository unavailable: {exc}')
        try:
            head = self.get_current_head()
            target = self.get_branch_head('developer')
            source = self.get_branch_head(result.source_branch)
            if (not head or head != target or target != result.post_commit
                    or source != result.approved_commit):
                errors.append('Post-merge branch or commit identity mismatch')
        except Exception as exc:
            errors.append(f'Post-merge identity unavailable: {exc}')
        try:
            pending = self.get_pending_operations()
            if pending:
                errors.append('Post-merge Git operation remains pending')
        except Exception as exc:
            errors.append(f'Post-merge safety unavailable: {exc}')
        if target:
            try:
                ancestor = self._command('merge-base', '--is-ancestor', result.approved_commit, target, check=False)
                if ancestor.returncode not in (0, 1):
                    raise ValueError(ancestor.stderr or 'Ancestry check failed')
                integrated = ancestor.returncode == 0
                if not integrated:
                    errors.append('Approved implementation is not integrated into developer')
                retained = self._command('merge-base', '--is-ancestor', result.pre_commit, target, check=False)
                if retained.returncode != 0:
                    errors.append('Pre-merge developer history is not retained: ' + retained.stderr)
            except Exception as exc:
                errors.append(f'Integration verification failed: {exc}')
        if not errors:
            try:
                # Object-only calculation: never checkout or run a trial merge.
                expected_tree = self._merge_tree(result.pre_commit, result.approved_commit)
                actual_tree = self._command('rev-parse', '--verify',
                    f'{result.post_commit}^{{tree}}').stdout.strip()
                content_matched = bool(actual_tree) and expected_tree == actual_tree
                if not content_matched:
                    errors.append('Post-merge content differs from expected merge content')
                # Natural merge alone accepts an already-integrated but reverted
                # change. Reintroducing the approved delta from its saved base
                # must be conflict-free and leave the actual tree unchanged.
                if self._command('merge-base', '--is-ancestor', base_commit,
                        result.approved_commit, check=False).returncode != 0:
                    raise ValueError('Approved base is not an ancestor of approved commit')
                retained_tree = self._merge_tree(result.post_commit, result.approved_commit,
                    base_commit=base_commit)
                retained_content = retained_tree == actual_tree
                if not retained_content:
                    errors.append('Approved content is missing or reverted in post-merge result')
            except Exception as exc:
                errors.append(f'Content verification unavailable: {exc}')
        return GitMergeVerification(state, head, target, source, pending, integrated, tuple(errors),
            expected_tree, actual_tree, content_matched, retained_content)

    def _merge_tree(self, target: str, approved: str, *, base_commit: str | None = None) -> str:
        arguments = ['merge-tree', '--write-tree']
        if base_commit is not None:
            arguments.append(f'--merge-base={base_commit}')
        result = self._command(*self._content_options(), *arguments, target, approved, check=False)
        if result.returncode != 0:
            raise ValueError('Conflict-free expected content unavailable: ' + result.stdout + result.stderr)
        lines = result.stdout.splitlines()
        if not lines:
            raise ValueError('Expected tree identifier unavailable')
        tree = lines[0].strip()
        # Validate the returned object instead of trusting an arbitrary output line.
        resolved = self._command('rev-parse', '--verify', f'{tree}^{{tree}}').stdout.strip()
        if not resolved or resolved != tree:
            raise ValueError('Invalid expected tree identifier')
        return tree

    def _content_options(self) -> tuple[str, ...]:
        # A configured external driver could silently discard changes or resolve
        # conflicts. Do not execute it to calculate (or produce) approved content.
        drivers = self._command('config', '--get-regexp', r'^merge\..*\.driver$', check=False)
        if drivers.returncode != 1:
            raise ValueError('Cannot establish ordinary merge content with custom or unreadable merge drivers')
        return ('-c', 'merge.default=text', '-c', 'merge.union.driver=false')

    def _command(self, *arguments: str, check: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(['git', *arguments], cwd=self._working_directory,
            check=check, capture_output=True, text=True, encoding='utf-8')
