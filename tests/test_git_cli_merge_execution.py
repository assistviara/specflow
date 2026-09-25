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
    verification = git.verify_merge(result, base_commit=base)
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
    assert result.command_success and git.verify_merge(result, base_commit=base).verified
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
    assert not git.verify_merge(result, base_commit=base).verified


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
    verification = git.verify_merge(result, base_commit=base)
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


def test_rejects_merge_that_preserves_ancestry_but_discards_approved_content(git_case):
    repo, base, approved, git = git_case
    run_git(repo, 'checkout', 'developer')
    (repo / 'developer.txt').write_text('independent work\n', encoding='utf-8')
    run_git(repo, 'add', 'developer.txt')
    run_git(repo, 'commit', '-m', 'developer work')
    before = run_git(repo, 'rev-parse', 'HEAD')
    run_git(repo, 'merge', '-s', 'ours', '--no-edit', approved)
    from application.git_merge_service import GitMergeResult
    result = GitMergeResult(str(repo), 'impl/approved', 'developer', approved, before,
        post_commit=run_git(repo, 'rev-parse', 'HEAD'), command_started=True, returncode=0)
    assert run_git(repo, 'merge-base', '--is-ancestor', approved, 'HEAD') == ''
    assert not (repo / 'approved.txt').exists()
    assert not git.verify_merge(result, base_commit=base).verified


def claimed_result(repo, approved, before):
    from application.git_merge_service import GitMergeResult
    return GitMergeResult(str(repo), 'impl/approved', 'developer', approved, before,
        post_commit=run_git(repo, 'rev-parse', 'HEAD'), command_started=True, returncode=0)


def test_rejects_extra_content_in_post_merge(git_case):
    repo, base, approved, git = git_case
    result = git.merge('impl/approved', approved, base)
    (repo / 'extra.txt').write_text('not approved', encoding='utf-8')
    run_git(repo, 'add', 'extra.txt')
    run_git(repo, 'commit', '-m', 'unexpected extra change')
    result = replace(result, post_commit=run_git(repo, 'rev-parse', 'HEAD'))
    verification = git.verify_merge(result, base_commit=base)
    assert not verification.verified and not verification.content_matched
    assert verification.expected_tree != verification.actual_tree


def test_rejects_already_integrated_but_reverted_approved_content(git_case):
    repo, base, approved, git = git_case
    run_git(repo, 'checkout', 'developer')
    run_git(repo, 'merge', '--ff-only', approved)
    run_git(repo, 'revert', '--no-edit', approved)
    before = run_git(repo, 'rev-parse', 'HEAD')
    result = claimed_result(repo, approved, before)
    verification = git.verify_merge(result, base_commit=base)
    assert verification.integrated and verification.content_matched
    assert not verification.approved_content_retained and not verification.verified
    assert not (repo / 'approved.txt').exists()


def test_same_file_nonconflicting_content_is_preserved_without_verification_writes(git_case):
    repo, _, _, git = git_case
    run_git(repo, 'checkout', 'developer')
    (repo / 'shared.txt').write_text(''.join(f'line {i}\n' for i in range(30)), encoding='utf-8')
    run_git(repo, 'add', 'shared.txt')
    run_git(repo, 'commit', '-m', 'shared base')
    base = run_git(repo, 'rev-parse', 'HEAD')
    run_git(repo, 'checkout', '-B', 'impl/approved')
    path = repo / 'shared.txt'
    path.write_text(path.read_text().replace('line 1\n', 'approved edit\n'), encoding='utf-8')
    run_git(repo, 'add', 'shared.txt')
    run_git(repo, 'commit', '-m', 'approved edit')
    approved = run_git(repo, 'rev-parse', 'HEAD')
    run_git(repo, 'checkout', 'developer')
    path.write_text(path.read_text().replace('line 28\n', 'developer edit\n'), encoding='utf-8')
    run_git(repo, 'add', 'shared.txt')
    run_git(repo, 'commit', '-m', 'developer edit')
    before = run_git(repo, 'rev-parse', 'HEAD')
    run_git(repo, 'checkout', 'impl/approved')
    result = git.merge('impl/approved', approved, before)
    content = path.read_bytes()
    index = (repo / '.git' / 'index').read_bytes()
    verification = git.verify_merge(result, base_commit=base)
    assert verification.verified and verification.approved_content_retained
    assert b'approved edit' in content and b'developer edit' in content
    assert path.read_bytes() == content
    assert (repo / '.git' / 'index').read_bytes() == index
    assert run_git(repo, 'rev-parse', 'HEAD') == result.post_commit
    assert run_git(repo, 'rev-parse', 'impl/approved') == approved


def test_conflicting_expected_content_is_rejected_without_resolution(git_case):
    repo, base, _, git = git_case
    (repo / 'tracked.txt').write_text('approved version\n', encoding='utf-8')
    run_git(repo, 'add', 'tracked.txt')
    run_git(repo, 'commit', '-m', 'approved edit')
    approved = run_git(repo, 'rev-parse', 'HEAD')
    run_git(repo, 'checkout', 'developer')
    (repo / 'tracked.txt').write_text('developer version\n', encoding='utf-8')
    run_git(repo, 'add', 'tracked.txt')
    run_git(repo, 'commit', '-m', 'developer edit')
    before = run_git(repo, 'rev-parse', 'HEAD')
    run_git(repo, 'merge', '-s', 'ours', '--no-edit', approved)
    result = claimed_result(repo, approved, before)
    content = (repo / 'tracked.txt').read_bytes()
    verification = git.verify_merge(result, base_commit=base)
    assert not verification.verified and verification.expected_tree is None
    assert any('Conflict-free' in error for error in verification.errors)
    assert (repo / 'tracked.txt').read_bytes() == content
    assert run_git(repo, 'rev-parse', 'HEAD') == result.post_commit
    assert not (repo / '.git' / 'MERGE_HEAD').exists()


@pytest.mark.parametrize('failure', ['error', 'empty', 'invalid'])
def test_expected_tree_acquisition_failure_is_not_success(git_case, monkeypatch, failure):
    import subprocess
    repo, base, approved, git = git_case
    result = git.merge('impl/approved', approved, base)
    original = git._command
    def command(*args, **kwargs):
        if 'merge-tree' in args:
            return subprocess.CompletedProcess(args, 128 if failure == 'error' else 0,
                'not-a-tree' if failure == 'invalid' else '', 'unavailable')
        return original(*args, **kwargs)
    monkeypatch.setattr(git, '_command', command)
    verification = git.verify_merge(result, base_commit=base)
    assert not verification.verified and not verification.content_matched
    assert any('Content verification unavailable' in e for e in verification.errors)


def test_custom_merge_driver_is_not_executed_for_content_verification(git_case):
    repo, base, approved, git = git_case
    result = git.merge('impl/approved', approved, base)
    run_git(repo, 'config', 'merge.custom.driver', 'echo unsafe > driver-ran.txt')
    verification = git.verify_merge(result, base_commit=base)
    assert not verification.verified
    assert any('merge drivers' in e for e in verification.errors)
    assert not (repo / 'driver-ran.txt').exists()


def test_already_integrated_content_with_independent_developer_change_is_valid(git_case):
    repo, base, approved, git = git_case
    run_git(repo, 'checkout', 'developer')
    run_git(repo, 'merge', '--ff-only', approved)
    (repo / 'independent.txt').write_text('developer change', encoding='utf-8')
    run_git(repo, 'add', 'independent.txt')
    run_git(repo, 'commit', '-m', 'independent change')
    before = run_git(repo, 'rev-parse', 'HEAD')
    verification = git.verify_merge(claimed_result(repo, approved, before), base_commit=base)
    assert verification.verified and verification.approved_content_retained
