import subprocess

import pytest

from infrastructure.git_cli_merge_service import GitCliMergeService
from test_git_repository_state_provider import make_clean_repository, run_git


def test_read_only_branch_head_and_operation_observations(tmp_path):
    repo, base = make_clean_repository(tmp_path)
    run_git(repo, 'checkout', '-b', 'impl/safety')
    (repo / 'tracked.txt').write_text('approved implementation\n', encoding='utf-8')
    run_git(repo, 'add', 'tracked.txt')
    run_git(repo, 'commit', '-m', 'implementation')
    git = GitCliMergeService(repo)
    head = run_git(repo, 'rev-parse', 'HEAD')
    before = {p: p.read_bytes() for p in repo.rglob('*') if p.is_file()}
    assert git.get_branch_head('impl/safety') == head
    assert git.get_branch_head('developer') == base
    assert git.get_current_head() == head
    assert git.get_pending_operations() == ()
    state = git.get_state(base)
    assert state.branch == 'impl/safety' and state.base_commit == base
    assert not state.git_status and not state.unavailable_evidence
    assert '+approved implementation' in state.git_diff
    # git status may refresh the index's stat cache; source and refs stay unchanged.
    assert all(p.read_bytes() == data for p, data in before.items() if p != repo / '.git' / 'index')
    assert run_git(repo, 'rev-parse', 'HEAD') == head


@pytest.mark.parametrize('marker', ['MERGE_HEAD', 'CHERRY_PICK_HEAD', 'REVERT_HEAD',
    'rebase-merge', 'rebase-apply', 'sequencer'])
def test_detects_unfinished_operations_without_running_them(tmp_path, marker):
    repo, base = make_clean_repository(tmp_path)
    path = repo / '.git' / marker
    if marker.endswith('HEAD'):
        path.write_text(base + '\n', encoding='utf-8')
    else:
        path.mkdir()
    assert GitCliMergeService(repo).get_pending_operations() == (marker,)
    assert path.exists()


def test_branch_must_be_local_and_exist(tmp_path):
    repo, base = make_clean_repository(tmp_path)
    git = GitCliMergeService(repo)
    for branch in ('missing', base, 'HEAD'):
        with pytest.raises(subprocess.CalledProcessError):
            git.get_branch_head(branch)


def test_inaccessible_repository_does_not_look_safe(tmp_path):
    git = GitCliMergeService(tmp_path / 'missing')
    with pytest.raises(OSError):
        git.get_pending_operations()
    with pytest.raises(OSError):
        git.get_branch_head('impl/missing')
