"""Initial Plan observations; untracked ignored files are excluded."""
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import stat
import subprocess


class SnapshotUnavailable(RuntimeError):
    """Observation is incomplete. Messages contain item names, never file contents."""


@dataclass(frozen=True)
class PlanRepositorySnapshot:
    identity: tuple
    head: bytes
    branch: bytes
    index: tuple
    files: dict[str, tuple]

    def differences(self, other):
        changes = [name for name in ('identity', 'head', 'branch', 'index')
                   if getattr(self, name) != getattr(other, name)]
        changes.extend(f'file: {name!r}' for name in sorted(self.files.keys() | other.files.keys())
                       if self.files.get(name) != other.files.get(name))
        return tuple(changes)


class PlanRepositorySnapshotProvider:
    def __init__(self, repository: Path):
        self.repository = Path(repository)

    def _git(self, *args, allow_absent=False):
        try:
            result = subprocess.run(
                ['git', '--no-optional-locks', *args], cwd=self.repository,
                env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'},
                capture_output=True, check=False,
            )
        except OSError:
            raise SnapshotUnavailable(f'Git observation unavailable: {args[0]}') from None
        if result.returncode != 0 and not (allow_absent and result.returncode == 1):
            raise SnapshotUnavailable(f'Git observation unavailable: {args[0]}')
        # Git can report inaccessible paths as warnings while exiting successfully.
        if result.stderr.strip():
            raise SnapshotUnavailable(f'Git observation incomplete: {args[0]}')
        return result.stdout

    @staticmethod
    def _identity(path):
        info = path.stat()
        return str(path.resolve(strict=True)), info.st_dev, info.st_ino

    @staticmethod
    def _read_file(path, *, missing_ok=False):
        try:
            before = path.lstat()
        except FileNotFoundError:
            if missing_ok:
                return ('missing',)
            raise
        mode = stat.S_IFMT(before.st_mode)
        executable = before.st_mode & 0o111
        if stat.S_ISLNK(before.st_mode):
            content = os.readlink(path)
        elif stat.S_ISREG(before.st_mode):
            digest = hashlib.sha256()
            with path.open('rb') as stream:
                # Refuse a file replaced between lstat and open.
                opened = os.fstat(stream.fileno())
                if (opened.st_dev, opened.st_ino, stat.S_IFMT(opened.st_mode)) != (
                        before.st_dev, before.st_ino, mode):
                    raise SnapshotUnavailable('File changed during observation')
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(block)
            content = digest.digest()
        else:
            raise SnapshotUnavailable('Unsupported file type')
        after = path.lstat()
        if (before.st_dev, before.st_ino, before.st_mode, before.st_size,
                before.st_mtime_ns, before.st_ctime_ns) != (
                after.st_dev, after.st_ino, after.st_mode, after.st_size,
                after.st_mtime_ns, after.st_ctime_ns):
            raise SnapshotUnavailable('File changed during observation')
        return mode, executable, content

    def capture(self) -> PlanRepositorySnapshot:
        item = 'repository identity'
        try:
            root = self.repository.resolve(strict=True)
            top = Path(os.fsdecode(self._git('rev-parse', '--show-toplevel').strip())).resolve(strict=True)
            if root != top:
                raise SnapshotUnavailable('Configured directory is not the Repository root')
            git_dir = Path(os.fsdecode(self._git('rev-parse', '--absolute-git-dir').strip()))
            identity = self._identity(root), self._identity(git_dir)
            item = 'HEAD / branch'
            branch = self._git('symbolic-ref', '-q', 'HEAD', allow_absent=True).strip()
            head = self._git('rev-parse', '--verify', '--quiet', 'HEAD^{commit}', allow_absent=True).strip()
            if not head:
                # Only a genuinely unborn branch may have no HEAD.
                if not branch or self._git('for-each-ref', '--format=%(refname)', branch.decode('utf-8')).strip():
                    raise SnapshotUnavailable('HEAD observation unavailable')
            item = 'index'
            index_path = Path(os.fsdecode(self._git('rev-parse', '--git-path', 'index').strip()))
            if not index_path.is_absolute():
                index_path = root / index_path
            if index_path.is_symlink():
                raise SnapshotUnavailable('Index is a link; observation unavailable')
            index = (self._read_file(index_path, missing_ok=True),
                     self._git('ls-files', '--stage', '-z'))
            cached = self._git('ls-files', '--cached', '-z')
            tracked = self._git('ls-tree', '-r', '--name-only', '-z', head.decode('ascii')) if head else b''
            untracked = self._git('ls-files', '--others', '--exclude-standard', '-z')
            untracked_names = {os.fsdecode(name) for name in untracked.split(b'\0') if name}
            names = {os.fsdecode(name) for name in (cached + tracked + untracked).split(b'\0') if name}
            files = {}
            for name in sorted(names):
                item = f'file: {name!r}'
                relative = Path(name)
                if relative.is_absolute() or relative.drive or '..' in relative.parts or '.git' in relative.parts:
                    raise SnapshotUnavailable('Unsafe Repository path')
                path = root / relative
                for parent in path.parents:
                    if parent == root:
                        break
                    if parent.is_symlink() or (hasattr(parent, 'is_junction') and parent.is_junction()):
                        raise SnapshotUnavailable('File parent is a link; observation unavailable')
                if hasattr(path, 'is_junction') and path.is_junction():
                    raise SnapshotUnavailable('Junction observation unavailable')
                files[name] = self._read_file(path, missing_ok=name not in untracked_names)
            return PlanRepositorySnapshot(identity, head, branch, index, files)
        except (OSError, ValueError, SnapshotUnavailable):
            raise SnapshotUnavailable(f'Repository observation unavailable ({item})') from None
