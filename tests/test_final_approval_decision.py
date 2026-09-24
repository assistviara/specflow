from dataclasses import asdict, replace
from enum import Enum
from unittest.mock import Mock

import pytest

from test_final_approval_target import target_case, request_for, execute
from test_final_approval_entry import entry_case
from test_review_handoff import handoff_case
from test_correction_continuation import continuation_case
from test_correction_routing import routing_case
from test_classify_review_result import result_case
from test_prepare_review_input import review_case


def test_receives_explicit_final_approval_for_the_frozen_target(target_case):
    from application.final_approval_decision import (
        FinalApprovalDecision, FinalApprovalDecisionInput, FinalApprovalDecisionUseCase,
    )
    target = execute(request_for(target_case))
    assert target.succeeded
    output = FinalApprovalDecisionUseCase().execute(
        FinalApprovalDecisionInput(target, 'Final Approval'))
    assert output.decision is FinalApprovalDecision.FINAL_APPROVAL
    assert output.is_final_approval
    assert not output.failures
    assert output.request.target is target


@pytest.fixture
def decision_target(target_case):
    target = execute(request_for(target_case))
    assert target.succeeded
    return target


def receive(target, decision=None):
    from application.final_approval_decision import FinalApprovalDecisionInput, FinalApprovalDecisionUseCase
    return FinalApprovalDecisionUseCase().execute(FinalApprovalDecisionInput(target, decision))


@pytest.mark.parametrize('label,member', [
    ('Final Approval', 'FINAL_APPROVAL'),
    ('Implementation Correction', 'IMPLEMENTATION_CORRECTION'),
    ('Plan Revision', 'PLAN_REVISION'),
    ('Specification Reconsideration', 'SPECIFICATION_RECONSIDERATION'),
    ('Cancellation', 'CANCELLATION'),
])
def test_identifies_only_the_explicit_selection(decision_target, label, member):
    from application.final_approval_decision import FinalApprovalDecision
    expected = FinalApprovalDecision[member]
    for supplied in (label, expected):
        output = receive(decision_target, supplied)
        assert output.decision is expected
        assert output.is_final_approval is (member == 'FINAL_APPROVAL')
        assert not output.failures


def test_pending_request_exposes_existing_human_review_material_without_decision(decision_target):
    output = receive(decision_target)
    assert output.decision is None
    assert not output.is_final_approval and not output.failures
    assert output.request.target is decision_target
    target = output.request.target
    assert target.artifact_hash == decision_target.artifact_hash
    assert target.request.artifact_path.is_file()
    entry = target.request.entry
    assert output.review is entry.request.handoff.request.continuation.request.review
    assert output.review.result == 'APPROVED'
    assert output.review.report is not None
    inp = output.review.review.prepared.review_input
    assert inp.evidence is not None and inp.saved_diff is not None
    assert target.artifact.implementation_branch == inp.evidence.identity.implementation_branch
    assert target.artifact.base_commit == inp.evidence.identity.base_commit
    assert target.artifact.head_commit == entry.head_commit
    assert target.artifact.implementation_evidence_reference == str(target.request.implementation_evidence_reference)
    assert target.artifact.git_diff_reference == str(target.request.git_diff_reference)
    assert target.artifact.review_report_reference == str(target.request.review_report_reference)


@pytest.mark.parametrize('decision', [
    '', ' ', 'pending', '未回答', '保留', 'Decisionなし',
    'reject', 'rejection', 'rejected', 'approve', 'approved', 'APPROVED',
    'yes', 'Final Approval ', 'final approval', 'FINAL_APPROVAL',
    'critical_change_approved', 'CRITICAL_CHANGE_APPROVAL',
    True, False, 1, {}, [], {'decision': 'Final Approval'},
])
def test_does_not_infer_a_decision_from_other_input(decision_target, decision):
    output = receive(decision_target, decision)
    assert output.decision is None and not output.is_final_approval
    assert [failure.code for failure in output.failures] == ['EXPLICIT_DECISION_REQUIRED']
    assert output.request.human_decision is decision


def test_other_decision_enum_is_not_reinterpreted(decision_target):
    class OtherDecision(str, Enum):
        APPROVAL = 'Final Approval'
    output = receive(decision_target, OtherDecision.APPROVAL)
    assert output.decision is None and output.failures
    assert not output.is_final_approval


@pytest.mark.parametrize('missing', ['target', 'artifact', 'artifact_hash', 'failure'])
def test_requires_established_target_before_accepting_decision(decision_target, missing):
    from application.final_approval_target import TargetFailure
    if missing == 'target':
        target = None
    elif missing == 'failure':
        target = replace(decision_target, failures=(TargetFailure('FAILED', 'not established'),))
    else:
        target = replace(decision_target, **{missing: None})
    output = receive(target, 'Final Approval')
    assert output.decision is None and not output.is_final_approval
    assert [failure.code for failure in output.failures] == ['TARGET_NOT_ESTABLISHED']


@pytest.mark.parametrize('decision', [
    'Final Approval', 'Implementation Correction', 'Plan Revision',
    'Specification Reconsideration', 'Cancellation', None, 'pending', 'rejection',
])
def test_receipt_preserves_target_and_has_no_record_routing_state_or_git_effects(
        decision_target, target_case, tmp_path, monkeypatch, decision):
    import core.approval_record_service as records
    import core.approval_validation as validation
    import application.state_transition as transitions
    build = Mock(side_effect=AssertionError('Approval Record construction is Target 4'))
    validate = Mock(side_effect=AssertionError('Approval Validation is Target 4'))
    transition = Mock(side_effect=AssertionError('No Target 3 state transition'))
    monkeypatch.setattr(records, 'build_approval_record_from_artifact', build)
    monkeypatch.setattr(validation, 'validate_approval_result', validate)
    monkeypatch.setattr(transitions, 'transition_state', transition)
    before = asdict(decision_target)
    files = {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    case = target_case[5]
    git_calls = list(case[3].mock_calls)
    output = receive(decision_target, decision)
    assert output.request.target is decision_target
    assert asdict(decision_target) == before
    assert {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()} == files
    build.assert_not_called()
    validate.assert_not_called()
    transition.assert_not_called()
    case[4][0]['approvals'].save.assert_not_called()
    case[4][3].run.assert_not_called()
    assert case[3].mock_calls == git_calls
