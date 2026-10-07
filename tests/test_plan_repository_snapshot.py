import os
import subprocess

import pytest

from infrastructure.plan_repository_snapshot import PlanRepositorySnapshotProvider, SnapshotUnavailable
from test_git_repository_state_provider import make_clean_repository, run_git


@pytest.fixture
def repository(tmp_path):
    root, _ = make_clean_repository(tmp_path)
    (root / '.gitignore').write_text('ignored\n')
    (root / 'ignored').write_text('private')
    (root / 'untracked').write_text('original')
    return root, PlanRepositorySnapshotProvider(root)


def test_dirty_state_is_allowed_and_observation_does_not_update_index(repository):
    root, provider = repository
    (root / 'tracked.txt').write_text('already dirty')
    index = root / '.git' / 'index'
    before_bytes, before_time = index.read_bytes(), index.stat().st_mtime_ns
    before = provider.capture()
    assert not before.differences(provider.capture())
    assert index.read_bytes() == before_bytes
    assert index.stat().st_mtime_ns == before_time


@pytest.mark.parametrize('name', ['tracked.txt', 'untracked'])
@pytest.mark.parametrize('operation', ['modify', 'delete', 'type', 'executable'])
def test_file_content_deletion_type_and_mode_changes(repository, name, operation):
    root, provider = repository
    before = provider.capture()
    path = root / name
    if operation == 'modify':
        path.write_text('changed')
    elif operation == 'delete':
        path.unlink()
    elif operation == 'type':
        path.unlink()
        path.mkdir()
        if name == 'untracked':
            assert f'file: {name!r}' in before.differences(provider.capture())
            return
        with pytest.raises(SnapshotUnavailable, match=name):
            provider.capture()
        return
    else:
        if os.name == 'nt':
            pytest.skip('Windows does not expose POSIX executable bits')
        path.chmod(0o755)
    assert f'file: {name!r}' in before.differences(provider.capture())


@pytest.mark.parametrize('staged', [True, False])
def test_file_addition(repository, staged):
    root, provider = repository
    before = provider.capture()
    (root / 'added').write_text('new')
    if staged:
        run_git(root, 'add', 'added')
    changes = before.differences(provider.capture())
    assert "file: 'added'" in changes
    assert ('index' in changes) is staged


@pytest.mark.parametrize('change', ['head', 'branch', 'index'])
def test_git_changes(repository, change):
    root, provider = repository
    before = provider.capture()
    if change == 'head':
        run_git(root, 'commit', '--allow-empty', '-m', 'new head')
    elif change == 'branch':
        run_git(root, 'checkout', '-b', 'other')
    else:
        # Index-only change, with unchanged worktree bytes.
        run_git(root, 'update-index', '--assume-unchanged', 'tracked.txt')
    assert change in before.differences(provider.capture())


def test_ignored_contents_and_additions_are_outside_mvp(repository):
    root, provider = repository
    before = provider.capture()
    (root / 'ignored').write_text('changed')
    assert not before.differences(provider.capture())
    (root / 'ignored').unlink()
    assert not before.differences(provider.capture())
    (root / 'ignored').write_text('new ignored file')
    assert not before.differences(provider.capture())


def test_tracked_ignored_file_is_still_compared(repository):
    root, provider = repository
    run_git(root, 'add', '-f', 'ignored')
    before = provider.capture()
    (root / 'ignored').write_text('changed')
    assert "file: 'ignored'" in before.differences(provider.capture())


def test_index_removed_path_is_still_compared_as_head_tracked(repository):
    root, provider = repository
    run_git(root, 'rm', '--cached', 'tracked.txt')
    before = provider.capture()
    (root / 'tracked.txt').write_text('changed')
    assert "file: 'tracked.txt'" in before.differences(provider.capture())


def test_git_failure_never_becomes_unchanged(repository, monkeypatch):
    _, provider = repository
    monkeypatch.setattr(subprocess, 'run', lambda *a, **kw: subprocess.CompletedProcess(a, 128, b'', b'secret'))
    with pytest.raises(SnapshotUnavailable, match='repository identity') as exc:
        provider.capture()
    assert 'secret' not in str(exc.value)


def test_read_failure_reports_path_without_contents(repository, monkeypatch):
    root, provider = repository
    original = provider._read_file
    def fail(path, **kwargs):
        if path.name == 'untracked':
            raise PermissionError('secret data')
        return original(path, **kwargs)
    monkeypatch.setattr(provider, '_read_file', fail)
    with pytest.raises(SnapshotUnavailable, match='untracked') as exc:
        provider.capture()
    assert 'secret data' not in str(exc.value)


def test_git_warning_means_incomplete_observation(repository, monkeypatch):
    _, provider = repository
    monkeypatch.setattr(subprocess, 'run', lambda *a, **kw: subprocess.CompletedProcess(a, 0, b'', b'private warning'))
    with pytest.raises(SnapshotUnavailable) as exc:
        provider.capture()
    assert 'private warning' not in str(exc.value)


def test_unborn_repository(tmp_path):
    run_git(tmp_path, 'init')
    provider = PlanRepositorySnapshotProvider(tmp_path)
    assert not provider.capture().differences(provider.capture())


def test_symlink_targets_are_compared_without_reading_external_contents(repository, tmp_path):
    root, provider = repository
    external = tmp_path / 'external'
    external.write_text('private')
    link = root / 'link'
    try:
        link.symlink_to(external)
    except OSError:
        pytest.skip('Symlink creation unavailable')
    before = provider.capture()
    external.write_text('changed outside repository')
    assert not before.differences(provider.capture())
    link.unlink()
    link.symlink_to(tmp_path / 'missing')
    assert "file: 'link'" in before.differences(provider.capture())


def test_directory_symlink_parent_is_not_followed(repository, tmp_path):
    root, provider = repository
    (root / 'dir').mkdir()
    (root / 'dir' / 'file').write_text('tracked')
    run_git(root, 'add', 'dir/file')
    (root / 'dir' / 'file').unlink()
    (root / 'dir').rmdir()
    try:
        (root / 'dir').symlink_to(tmp_path, target_is_directory=True)
    except OSError:
        pytest.skip('Symlink creation unavailable')
    with pytest.raises(SnapshotUnavailable, match='dir/file'):
        provider.capture()
