import json
from dataclasses import asdict, replace
from unittest.mock import Mock

import pytest

from test_final_approval_decision import decision_target, receive
from test_final_approval_target import target_case
from test_final_approval_entry import entry_case
from test_review_handoff import handoff_case
from test_correction_continuation import continuation_case
from test_correction_routing import routing_case
from test_classify_review_result import result_case
from test_prepare_review_input import review_case


def test_explicit_plan_revision_returns_only_to_plan_without_state_transition(decision_target):
    from application.final_approval_routing import FinalApprovalRoutingInput, FinalApprovalRoutingUseCase
    from application.correction_routing import ReturnDestination
    decision = receive(decision_target, 'Plan Revision')
    entry = decision_target.request.entry.request
    before = entry.state_file.read_bytes()
    history = {p: p.read_bytes() for p in entry.history_dir.glob('*.json')}
    request = FinalApprovalRoutingInput(decision, 'Human requested a plan revision.')
    output = FinalApprovalRoutingUseCase().execute(request)
    assert output.routed and not output.failures
    assert output.destination == ReturnDestination.PLAN
    assert output.request.decision is decision
    assert output.request.reason == request.reason
    assert output.transition is None
    assert output.approval_for_next_stage is None
    assert entry.state_file.read_bytes() == before
    assert {p: p.read_bytes() for p in entry.history_dir.glob('*.json')} == history


@pytest.fixture
def approval(decision_target, tmp_path):
    from application.final_approval_record import FinalApprovalRecordInput, FinalApprovalRecordUseCase
    from infrastructure.json_approval_record_repository import JsonApprovalRecordRepository
    request = FinalApprovalRecordInput(receive(decision_target, 'Final Approval'),
        'final-001', '2026-09-24T12:00:00+09:00', 'Human approved.')
    result = FinalApprovalRecordUseCase(JsonApprovalRecordRepository(tmp_path / 'approvals')).execute(request)
    assert result.approval_valid
    return result


def route(target, selection, approval=None, reason='Human supplied reason.', references=()):
    from application.final_approval_routing import FinalApprovalRoutingInput, FinalApprovalRoutingUseCase
    return FinalApprovalRoutingUseCase().execute(FinalApprovalRoutingInput(
        receive(target, selection), reason, approval, references))


@pytest.mark.parametrize('selection,destination,state', [
    ('Final Approval', 'UC-12 Merge Approved Implementation', 'final_approval_pending'),
    ('Implementation Correction', 'Codex再実装工程', 'correction_requested'),
    ('Plan Revision', 'Plan修正工程', 'final_approval_pending'),
    ('Specification Reconsideration', 'Specification策定工程', 'final_approval_pending'),
    ('Cancellation', 'cancelled', 'cancelled'),
])
def test_routes_only_selected_decision_and_preserves_context(
        decision_target, approval, target_case, tmp_path, monkeypatch, selection, destination, state):
    import application.final_approval_routing as module
    import application.final_approval_record as records
    entry = decision_target.request.entry.request
    before = asdict(decision_target), asdict(approval)
    files = {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    git = target_case[5][3]
    git_calls = list(git.mock_calls)
    transition = Mock(wraps=module.transition_state)
    build = Mock(side_effect=AssertionError('Routing must not build Approval Records'))
    monkeypatch.setattr(module, 'transition_state', transition)
    monkeypatch.setattr(records, 'build_approval_record_from_artifact', build)
    references = ('review.report', str(decision_target.request.artifact_path))
    reason = 'Human explicitly selected: ' + selection
    output = route(decision_target, selection, approval, reason, references)
    assert output.routed and not output.failures
    assert output.destination == destination
    assert output.request.decision.decision.value == selection
    assert output.request.reason == reason and output.request.references == references
    assert output.request.decision.request.target is decision_target
    assert output.request.approval is approval
    assert output.approval_for_next_stage is (approval if selection == 'Final Approval' else None)
    assert (asdict(decision_target), asdict(approval)) == before
    assert json.loads(entry.state_file.read_text())['status'] == state
    expected_files = set(files)
    if state != 'final_approval_pending':
        transition.assert_called_once_with(entry.state_file, entry.history_dir, output.transition)
        assert output.transition['from_state'] == 'final_approval_pending'
        assert output.transition['to_state'] == state
        assert output.transition['reason'] == reason
        history_file = entry.history_dir / (output.transition['transition_id'] + '.json')
        assert json.loads(history_file.read_text()) == output.transition
        expected_files.add(history_file)
    else:
        assert output.transition is None
        transition.assert_not_called()
        assert entry.state_file.read_bytes() == files[entry.state_file]
    assert set(p for p in tmp_path.rglob('*') if p.is_file()) == expected_files
    assert all(p.read_bytes() == content for p, content in files.items() if p != entry.state_file)
    assert git.mock_calls == git_calls
    target_case[5][4][3].run.assert_not_called()
    build.assert_not_called()


@pytest.mark.parametrize('selection', [None, 'pending', '', 'reject', 'rejection', 'approved',
    'APPROVED', 'CRITICAL_CHANGE_APPROVAL', 'Final Approval ', True])
def test_no_route_is_inferred_from_missing_or_ambiguous_decision(decision_target, approval, tmp_path, selection):
    files = {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    output = route(decision_target, selection, approval)
    assert not output.routed and output.destination is None
    assert output.transition is None and output.approval_for_next_stage is None
    assert output.failures
    assert {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()} == files


@pytest.mark.parametrize('kind', ['missing', 'save_failed', 'invalid', 'failure', 'record_missing', 'other_target'])
def test_final_approval_requires_matching_valid_target_four_result(decision_target, approval, kind):
    from application.final_approval_record import RecordFailure
    if kind == 'missing':
        approval = None
    elif kind == 'save_failed':
        approval = replace(approval, saved=False)
    elif kind == 'invalid':
        approval = replace(approval, approval_validation_result=replace(approval.approval_validation_result, is_valid=False))
    elif kind == 'failure':
        approval = replace(approval, failures=(RecordFailure('FAILURE', 'not valid'),))
    elif kind == 'record_missing':
        approval = replace(approval, approval_record=None)
    else:
        other_target = replace(decision_target, artifact_hash='other-target-hash')
        approval = replace(approval, request=replace(approval.request, decision=receive(other_target, 'Final Approval')))
    output = route(decision_target, 'Final Approval', approval)
    assert not output.routed and output.destination is None
    assert output.approval_for_next_stage is None and output.transition is None
    assert [f.code for f in output.failures] == ['FINAL_APPROVAL_NOT_VALID']


@pytest.mark.parametrize('field,value', [('artifact_path', 'other.json'), ('artifact_hash', 'bad-hash'),
    ('decision', 'rejected'), ('artifact_type', 'critical_change_request')])
def test_inconsistent_record_cannot_enter_final_approval_route(decision_target, approval, field, value):
    approval = replace(approval, approval_record={**approval.approval_record, field: value})
    output = route(decision_target, 'Final Approval', approval)
    assert not output.routed and output.failures
    assert output.approval_for_next_stage is None and output.transition is None


def test_changed_target_does_not_reuse_old_approval(decision_target, approval):
    path = decision_target.request.artifact_path
    data = json.loads(path.read_text())
    data['head_commit'] = 'c' * 40
    path.write_text(json.dumps(data), encoding='utf-8')
    output = route(decision_target, 'Final Approval', approval)
    assert not output.routed and output.failures
    assert output.approval_for_next_stage is None


@pytest.mark.parametrize('selection', ['Implementation Correction', 'Cancellation'])
@pytest.mark.parametrize('part', ['state', 'history'])
def test_state_or_history_failure_is_not_success_and_is_not_retried(
        decision_target, approval, monkeypatch, selection, part):
    import application.state_transition as transitions
    entry = decision_target.request.entry.request
    original_history = {p: p.read_bytes() for p in entry.history_dir.glob('*.json')}
    fail = Mock(side_effect=OSError(part + ' failed'))
    monkeypatch.setattr(transitions,
        'save_current_state' if part == 'state' else 'save_state_transition_history', fail)
    output = route(decision_target, selection, approval)
    assert not output.routed and output.destination is None
    assert output.approval_for_next_stage is None
    assert [f.code for f in output.failures] == ['STATE_HISTORY_PERSISTENCE_FAILED']
    assert part + ' failed' in output.failures[0].detail
    assert output.transition is not None
    assert output.request.approval is approval
    assert fail.call_count == 1
    expected = ('correction_requested' if selection == 'Implementation Correction' else 'cancelled')
    assert json.loads(entry.state_file.read_text())['status'] == (expected if part == 'history' else 'final_approval_pending')
    assert {p: p.read_bytes() for p in entry.history_dir.glob('*.json')} == original_history


@pytest.mark.parametrize('selection', ['Implementation Correction', 'Plan Revision',
    'Specification Reconsideration', 'Cancellation', 'Final Approval'])
def test_no_decision_can_restart_cancelled_workflow(decision_target, approval, selection):
    state_file = decision_target.request.entry.request.state_file
    state_file.write_text('{"status": "cancelled"}', encoding='utf-8')
    output = route(decision_target, selection, approval)
    assert not output.routed and output.failures and output.transition is None
    assert state_file.read_text() == '{"status": "cancelled"}'


@pytest.mark.parametrize('selection', ['Implementation Correction', 'Plan Revision',
    'Specification Reconsideration', 'Cancellation'])
def test_non_approval_route_does_not_require_approval_record(decision_target, selection):
    output = route(decision_target, selection)
    assert output.routed and not output.failures
    assert output.approval_for_next_stage is None


@pytest.mark.parametrize('reason', [None, '', ' '])
def test_reason_is_not_invented(decision_target, reason):
    output = route(decision_target, 'Plan Revision', reason=reason)
    assert not output.routed and output.failures
    assert output.request.reason is reason
    assert output.transition is None


def test_inconsistent_human_receipt_is_not_routed(decision_target):
    from application.final_approval_routing import FinalApprovalRoutingInput, FinalApprovalRoutingUseCase
    decision = receive(decision_target, 'Plan Revision')
    decision = replace(decision, request=replace(decision.request, human_decision='Cancellation'))
    output = FinalApprovalRoutingUseCase().execute(FinalApprovalRoutingInput(decision, 'reason'))
    assert not output.routed and output.failures and output.transition is None


def test_state_read_failure_does_not_route(decision_target):
    decision_target.request.entry.request.state_file.unlink()
    output = route(decision_target, 'Implementation Correction')
    assert not output.routed and output.failures and output.transition is None
