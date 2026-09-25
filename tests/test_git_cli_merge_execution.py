from dataclasses import replace

import pytest

from infrastructure.git_cli_merge_service import GitCliMergeService
from test_git_repository_state_provider import make_clean_repository, run_git


@pytest.fixture
def git_case(tmp_path):
    repo, base = make_clean_repository(tmp_path)
    run_git(repo, 'checkout', '-b', 'impl/approved')
    (repo / 'approved.txt').write_text('approved implementation\n', encoding='utf-8')
    run_git(repo, 'add', 'approved.txt')
    run_git(repo, 'commit', '-m', 'approved implementation')
    approved = run_git(repo, 'rev-parse', 'HEAD')
    return repo, base, approved, GitCliMergeService(repo)


def test_merges_approved_commit_into_developer_and_verifies_separately(git_case):
    repo, base, approved, git = git_case
    result = git.merge('impl/approved', approved, base)
    assert result.command_success and not result.errors and not result.conflicts
    assert result.pre_commit == base and result.approved_commit == approved
    assert result.post_commit == approved
    assert result.source_branch == 'impl/approved' and result.target_branch == 'developer'
    assert run_git(repo, 'branch', '--show-current') == 'developer'
    assert run_git(repo, 'rev-parse', 'impl/approved') == approved
    verification = git.verify_merge(result)
    assert verification.verified and verification.integrated
    assert verification.current_head == verification.target_head == approved
    assert not verification.repository_state.git_status


def test_diverged_branches_merge_without_rewriting_source(git_case):
    repo, base, approved, git = git_case
    run_git(repo, 'checkout', 'developer')
    (repo / 'developer.txt').write_text('existing developer work\n', encoding='utf-8')
    run_git(repo, 'add', 'developer.txt')
    run_git(repo, 'commit', '-m', 'developer work')
    target = run_git(repo, 'rev-parse', 'HEAD')
    run_git(repo, 'checkout', 'impl/approved')
    result = git.merge('impl/approved', approved, target)
    assert result.command_success and git.verify_merge(result).verified
    assert result.post_commit not in (approved, target)
    assert (repo / 'approved.txt').read_text() == 'approved implementation\n'
    assert (repo / 'developer.txt').read_text() == 'existing developer work\n'
    assert run_git(repo, 'rev-parse', 'impl/approved') == approved


def test_conflict_is_preserved_without_resolution_or_retry(git_case):
    repo, base, _, git = git_case
    (repo / 'tracked.txt').write_text('source version\n', encoding='utf-8')
    run_git(repo, 'add', 'tracked.txt')
    run_git(repo, 'commit', '-m', 'source edit')
    approved = run_git(repo, 'rev-parse', 'HEAD')
    run_git(repo, 'checkout', 'developer')
    (repo / 'tracked.txt').write_text('target version\n', encoding='utf-8')
    run_git(repo, 'add', 'tracked.txt')
    run_git(repo, 'commit', '-m', 'target edit')
    target = run_git(repo, 'rev-parse', 'HEAD')
    run_git(repo, 'checkout', 'impl/approved')
    result = git.merge('impl/approved', approved, target)
    assert result.command_started and not result.command_success
    assert result.conflicts == ('tracked.txt',) and result.errors
    assert result.repository_state.branch == 'developer'
    assert 'UU tracked.txt' in result.repository_state.git_status
    assert run_git(repo, 'rev-parse', 'developer') == target
    assert run_git(repo, 'rev-parse', 'impl/approved') == approved
    assert (repo / '.git' / 'MERGE_HEAD').exists()
    assert '<<<<<<<' in (repo / 'tracked.txt').read_text()
    assert not git.verify_merge(result).verified


@pytest.mark.parametrize('change', ['dirty', 'head', 'source_missing', 'target_missing', 'pending'])
def test_changed_repository_does_not_start_merge(git_case, change):
    repo, base, approved, git = git_case
    if change == 'dirty':
        (repo / 'unapproved.txt').write_text('unapproved', encoding='utf-8')
    elif change == 'head':
        approved = base
    elif change == 'source_missing':
        run_git(repo, 'checkout', 'developer')
        run_git(repo, 'branch', '-D', 'impl/approved')
    elif change == 'target_missing':
        run_git(repo, 'branch', '-D', 'developer')
    else:
        (repo / '.git' / 'MERGE_HEAD').write_text(base + '\n', encoding='utf-8')
    head = run_git(repo, 'rev-parse', 'HEAD')
    result = git.merge('impl/approved', approved, base)
    assert not result.command_started and not result.command_success and result.errors
    assert run_git(repo, 'rev-parse', 'HEAD') == head


@pytest.mark.parametrize('change', ['branch', 'head_unavailable', 'not_integrated', 'dirty', 'source_changed', 'pending'])
def test_post_merge_verification_detects_independent_failures(git_case, monkeypatch, change):
    repo, base, approved, git = git_case
    result = git.merge('impl/approved', approved, base)
    assert result.command_success
    if change == 'branch':
        run_git(repo, 'checkout', 'impl/approved')
    elif change == 'head_unavailable':
        def unavailable():
            raise OSError('HEAD unavailable')
        monkeypatch.setattr(git, 'get_current_head', unavailable)
    elif change == 'not_integrated':
        # Simulate a command result that claims success without integration.
        run_git(repo, 'reset', '--hard', base)
        result = replace(result, post_commit=base)
    elif change == 'dirty':
        (repo / 'unapproved.txt').write_text('unapproved', encoding='utf-8')
    elif change == 'source_changed':
        run_git(repo, 'update-ref', 'refs/heads/impl/approved', base)
    else:
        (repo / '.git' / 'MERGE_HEAD').write_text(base + '\n', encoding='utf-8')
    verification = git.verify_merge(result)
    assert not verification.verified and verification.errors
    if change == 'not_integrated':
        assert not verification.integrated


def test_merge_command_failure_retains_stdout_stderr(git_case, monkeypatch):
    import subprocess
    _, base, approved, git = git_case
    command = git._command
    calls = []
    def failing(*args, **kwargs):
        if 'merge' in args:
            calls.append(args)
            return subprocess.CompletedProcess(args, 128, 'merge output', 'merge error')
        return command(*args, **kwargs)
    monkeypatch.setattr(git, '_command', failing)
    result = git.merge('impl/approved', approved, base)
    assert not result.command_success and result.returncode == 128
    assert result.stdout == 'merge output' and result.stderr == 'merge error'
    assert len(calls) == 1
