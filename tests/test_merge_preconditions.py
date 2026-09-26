from dataclasses import asdict, replace
from unittest.mock import Mock
import json

import pytest

from test_final_approval_routing import approval, route
from test_final_approval_decision import decision_target, receive
from test_final_approval_target import target_case
from test_final_approval_entry import entry_case
from test_review_handoff import handoff_case
from test_correction_continuation import continuation_case
from test_correction_routing import routing_case
from test_classify_review_result import result_case
from test_prepare_review_input import review_case


@pytest.fixture
def merge_case(decision_target, approval, tmp_path):
    from infrastructure.json_approval_record_repository import JsonApprovalRecordRepository
    routed = route(decision_target, 'Final Approval', approval)
    assert routed.routed
    git = Mock()
    git.get_state.return_value = replace(decision_target.request.entry.repository_state, git_status='')
    git.get_current_head.return_value = decision_target.artifact.head_commit
    git.get_branch_head.side_effect = lambda branch: (
        decision_target.artifact.head_commit if branch == decision_target.artifact.implementation_branch
        else decision_target.artifact.base_commit)
    git.get_pending_operations.return_value = ()
    return routed, git, JsonApprovalRecordRepository(tmp_path / 'approvals')


def test_valid_approval_does_not_allow_observed_head_mismatch(merge_case):
    from application.merge_preconditions import MergePreconditionsUseCase
    routed, git, repository = merge_case
    before = asdict(routed)
    git.get_current_head.return_value = 'c' * 40
    output = MergePreconditionsUseCase(git, repository).execute(routed)
    assert not output.merge_ready
    assert any(f.code == 'HEAD_MISMATCH' for f in output.failures), output.failures
    assert output.observed_head == 'c' * 40
    assert output.request is routed
    assert asdict(routed) == before
    git.merge.assert_not_called()


def check(case):
    from application.merge_preconditions import MergePreconditionsUseCase
    routed, git, repository = case
    return MergePreconditionsUseCase(git, repository).execute(routed)


def with_target(routed, target):
    decision = replace(routed.request.decision, request=replace(routed.request.decision.request, target=target))
    approval = replace(routed.request.approval, request=replace(routed.request.approval.request, decision=decision))
    return replace(routed, request=replace(routed.request, decision=decision, approval=approval))


@pytest.mark.parametrize('failure', [None, 'head', 'repository'])
def test_readiness_preserves_inputs_files_and_only_observes_git(merge_case, tmp_path, monkeypatch, failure):
    import application.state_transition as transitions
    import application.final_approval_record as records
    routed, git, repository = merge_case
    if failure == 'head':
        git.get_current_head.return_value = 'changed'
    elif failure == 'repository':
        git.get_state.side_effect = OSError('inaccessible')
    before = asdict(routed)
    files = {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    save = Mock(side_effect=AssertionError('No Approval save'))
    transition = Mock(side_effect=AssertionError('No transition'))
    build = Mock(side_effect=AssertionError('No Approval construction'))
    monkeypatch.setattr(repository, 'save', save)
    monkeypatch.setattr(transitions, 'transition_state', transition)
    monkeypatch.setattr(records, 'build_approval_record_from_artifact', build)
    output = check(merge_case)
    assert output.merge_ready is (failure is None), output.failures
    assert asdict(routed) == before
    assert {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()} == files
    assert output.approval_validation.is_valid
    assert output.approval_record == repository.get('final-001')
    assert output.observed_head == git.get_current_head.return_value
    assert output.observed_branch_head == routed.request.decision.request.target.artifact.head_commit
    git.get_state.assert_called_once()
    git.get_current_head.assert_called_once()
    assert git.get_branch_head.call_count == 2
    git.get_pending_operations.assert_called_once()
    assert {call[0] for call in git.mock_calls} == {
        'get_state', 'get_current_head', 'get_branch_head', 'get_pending_operations'}
    save.assert_not_called()
    transition.assert_not_called()
    build.assert_not_called()


@pytest.mark.parametrize('field,value,code', [
    ('branch', 'other', 'BRANCH_MISMATCH'), ('branch', '', 'BRANCH_MISMATCH'),
    ('base_commit', '', 'BASE_COMMIT_MISMATCH'), ('base_commit', 'c' * 40, 'BASE_COMMIT_MISMATCH'),
    ('git_diff', 'new changes', 'DIFF_MISMATCH'),
    ('git_status', '?? unexpected.py', 'WORKING_TREE_NOT_READY'),
    ('git_status', ' M tracked.py', 'WORKING_TREE_NOT_READY'),
    ('git_status', 'M  tracked.py', 'WORKING_TREE_NOT_READY'),
    ('git_status', 'UU conflict.py', 'WORKING_TREE_NOT_READY'),
    ('unavailable_evidence', ('git_status',), 'REPOSITORY_INFORMATION_MISSING'),
])
def test_repository_fact_mismatches_are_not_ready(merge_case, field, value, code):
    routed, git, _ = merge_case
    before = asdict(routed)
    git.get_state.return_value = replace(git.get_state.return_value, **{field: value})
    output = check(merge_case)
    assert not output.merge_ready
    assert any(f.code == code for f in output.failures)
    assert output.observed_repository is git.get_state.return_value
    assert asdict(routed) == before


@pytest.mark.parametrize('operation,code', [
    ('get_state', 'REPOSITORY_ACCESS_FAILED'), ('get_current_head', 'HEAD_UNAVAILABLE'),
    ('get_branch_head', 'SOURCE_BRANCH_UNAVAILABLE'),
    ('get_pending_operations', 'REPOSITORY_SAFETY_UNAVAILABLE'),
])
def test_technical_failure_keeps_other_observations_without_retry(merge_case, operation, code):
    git = merge_case[1]
    getattr(git, operation).side_effect = OSError('technical failure')
    output = check(merge_case)
    assert not output.merge_ready
    assert any(f.code == code and 'technical failure' in f.detail for f in output.failures)
    assert getattr(git, operation).call_count == (2 if operation == 'get_branch_head' else 1)
    if operation != 'get_current_head':
        assert output.observed_head == git.get_current_head.return_value


@pytest.mark.parametrize('value', [None, '', ' '])
def test_current_head_unavailable_is_not_ready(merge_case, value):
    merge_case[1].get_current_head.return_value = value
    output = check(merge_case)
    assert not output.merge_ready
    assert any(f.code == 'HEAD_MISMATCH' for f in output.failures)


@pytest.mark.parametrize('source,value,code', [
    (True, '', 'SOURCE_BRANCH_UNAVAILABLE'), (True, 'changed', 'BRANCH_HEAD_MISMATCH'),
    (False, '', 'DESTINATION_BRANCH_UNAVAILABLE'),
])
def test_branch_existence_and_source_tip_are_checked(merge_case, source, value, code):
    routed, git, _ = merge_case
    artifact = routed.request.decision.request.target.artifact
    git.get_branch_head.side_effect = lambda branch: value if ((branch == artifact.implementation_branch) == source) else artifact.head_commit
    output = check(merge_case)
    assert not output.merge_ready
    assert any(f.code == code for f in output.failures)


@pytest.mark.parametrize('pending', [('MERGE_HEAD',), ('rebase-merge',), None])
def test_pending_or_unknown_repository_safety_is_not_ready(merge_case, pending):
    merge_case[1].get_pending_operations.return_value = pending
    output = check(merge_case)
    assert not output.merge_ready
    assert output.pending_operations == pending


@pytest.mark.parametrize('field', ['implementation_evidence_reference', 'git_diff_reference', 'review_report_reference'])
@pytest.mark.parametrize('change', ['missing', 'changed'])
def test_required_references_must_still_identify_approved_contents(merge_case, field, change):
    from pathlib import Path
    target = merge_case[0].request.decision.request.target
    path = Path(getattr(target.artifact, field))
    if change == 'missing':
        path.unlink()
    elif field == 'implementation_evidence_reference':
        data = json.loads(path.read_text(encoding='utf-8'))
        data['identity']['base_commit'] = 'changed'
        path.write_text(json.dumps(data), encoding='utf-8')
    else:
        path.write_bytes(path.read_bytes() + b'changed')
    output = check(merge_case)
    assert not output.merge_ready and output.failures
    assert merge_case[1].mock_calls == []


@pytest.mark.parametrize('change', ['missing', 'bytes', 'identity'])
def test_target_changes_do_not_reuse_old_approval(merge_case, change):
    path = merge_case[0].request.decision.request.target.request.artifact_path
    if change == 'missing':
        path.unlink()
    elif change == 'bytes':
        path.write_bytes(path.read_bytes() + b'\n')
    else:
        data = json.loads(path.read_text())
        data['head_commit'] = 'changed'
        path.write_text(json.dumps(data), encoding='utf-8')
    output = check(merge_case)
    assert not output.merge_ready and output.failures


@pytest.mark.parametrize('field,value', [
    ('artifact_path', 'other.json'), ('artifact_hash', 'wrong'), ('decision', 'rejected'),
    ('artifact_type', 'critical_change_request'),
])
def test_reloads_and_validates_current_approval_record(merge_case, field, value):
    repository = merge_case[2]
    record = repository.get('final-001')
    repository.save({**record, field: value})
    output = check(merge_case)
    assert not output.merge_ready
    assert output.approval_record[field] == value
    assert not output.approval_validation.is_valid
    assert merge_case[1].mock_calls == []


def test_missing_saved_approval_is_not_replaced_by_dto(merge_case):
    (merge_case[2].approvals_dir / 'final-001.json').unlink()
    output = check(merge_case)
    assert not output.merge_ready
    assert any(f.code == 'APPROVAL_UNAVAILABLE' for f in output.failures)


@pytest.mark.parametrize('selection', [None, 'pending', 'APPROVED', 'Implementation Correction', 'Plan Revision',
    'Specification Reconsideration', 'Cancellation'])
def test_only_final_approval_route_can_be_checked(merge_case, selection):
    routed, git, repository = merge_case
    target = routed.request.decision.request.target
    changed = replace(routed, request=replace(routed.request, decision=receive(target, selection)))
    output = check((changed, git, repository))
    assert not output.merge_ready and output.failures
    assert git.mock_calls == []


@pytest.mark.parametrize('field', ['implementation_branch', 'base_commit', 'implementation_id'])
def test_saved_implementation_identity_must_match_target(merge_case, field):
    from test_final_approval_target import with_identity
    from uuid import uuid4
    routed, git, repository = merge_case
    target = routed.request.decision.request.target
    entry = with_identity(target.request.entry, **{field: uuid4() if field == 'implementation_id' else 'changed'})
    target = replace(target, request=replace(target.request, entry=entry))
    changed = with_target(routed, target)
    output = check((changed, git, repository))
    assert not output.merge_ready and output.failures


@pytest.mark.parametrize('change', ['result', 'report', 'issue', 'specification', 'input'])
def test_phase_five_information_is_rechecked(merge_case, change):
    from test_final_approval_entry import change_review, change_input
    routed, git, repository = merge_case
    target = routed.request.decision.request.target
    handoff = target.request.entry.request.handoff
    if change == 'result':
        handoff = change_review(handoff, result='REVISION_REQUIRED')
    elif change == 'report':
        handoff = change_review(handoff, report=None)
    elif change == 'issue':
        handoff = replace(handoff, unresolved_issues=('Human decision required',))
    elif change == 'specification':
        handoff = change_input(handoff, specification=None)
    else:
        review = handoff.request.continuation.request.review.review
        handoff = change_review(handoff, review=replace(review, prepared=replace(review.prepared, review_input=None)))
    entry = replace(target.request.entry, request=replace(target.request.entry.request, handoff=handoff))
    changed = with_target(routed, replace(target, request=replace(target.request, entry=entry)))
    output = check((changed, git, repository))
    assert not output.merge_ready and output.failures
    assert git.mock_calls == []
