from dataclasses import asdict, replace
import hashlib
import json

import pytest

from test_final_approval_entry import entry_case, run_entry
from test_review_handoff import handoff_case
from test_correction_continuation import continuation_case
from test_correction_routing import routing_case
from test_classify_review_result import result_case
from test_prepare_review_input import review_case


@pytest.fixture
def target_case(entry_case, tmp_path):
    from infrastructure.json_implementation_evidence_repository import JsonImplementationEvidenceRepository
    entry = run_entry(entry_case)
    assert entry.entered
    inp = entry.request.handoff.request.continuation.request.review.review.prepared.review_input
    evidence = JsonImplementationEvidenceRepository(tmp_path / 'evidence').save(inp.evidence)
    return entry, tmp_path / 'final_target.json', evidence, inp.saved_diff.path, tmp_path / 'review_report.json', entry_case


def test_freezes_final_approval_target_with_stable_hash_without_approval(target_case):
    from application.final_approval_target import FinalApprovalTargetInput, FinalApprovalTargetUseCase, load_final_approval_target, artifact_hash
    entry, path, evidence, diff, report, case = target_case
    before = asdict(entry)
    original_files = {p: p.read_bytes() for p in path.parent.rglob('*') if p.is_file()}
    output = FinalApprovalTargetUseCase().execute(FinalApprovalTargetInput(entry, path, evidence, diff, report))
    assert output.succeeded and not output.failures
    saved = load_final_approval_target(path)
    identity = entry.request.handoff.request.continuation.request.review.review.prepared.review_input.evidence.identity
    assert asdict(saved) == dict(implementation_branch=identity.implementation_branch,
        head_commit=entry.head_commit, base_commit=identity.base_commit,
        implementation_evidence_reference=str(evidence), git_diff_reference=str(diff), review_report_reference=str(report))
    assert saved == output.artifact
    assert output.artifact_hash == hashlib.sha256(path.read_bytes()).hexdigest() == artifact_hash(path)
    assert entry.head_commit != identity.base_commit
    existing_report = entry.request.handoff.request.continuation.request.review.report
    assert json.loads(report.read_text(encoding='utf-8')) == json.loads(json.dumps(asdict(existing_report)))
    assert asdict(entry) == before
    assert all(p.read_bytes() == content for p, content in original_files.items())
    assert set(p for p in path.parent.rglob('*') if p.is_file()) == set(original_files) | {path, report}
    case[4][0]['approvals'].save.assert_not_called()
    case[4][3].run.assert_not_called()
    case[3].merge.assert_not_called()


def request_for(case):
    from application.final_approval_target import FinalApprovalTargetInput
    return FinalApprovalTargetInput(*case[:5])


def execute(request):
    from application.final_approval_target import FinalApprovalTargetUseCase
    return FinalApprovalTargetUseCase().execute(request)


def with_identity(entry, **changes):
    # Alter only a copy of the established entry to exercise missing inputs.
    handoff = entry.request.handoff
    continuation = handoff.request.continuation
    review = continuation.request.review
    prepared = review.review.prepared
    inp = prepared.review_input
    evidence = replace(inp.evidence, identity=replace(inp.evidence.identity, **changes))
    review = replace(review, review=replace(review.review, prepared=replace(prepared, review_input=replace(inp, evidence=evidence))))
    continuation = replace(continuation, request=replace(continuation.request, review=review))
    return replace(entry, request=replace(entry.request, handoff=replace(handoff, request=replace(handoff.request, continuation=continuation))))


@pytest.mark.parametrize('missing', ['entry', 'entry_failed', 'implementation_branch', 'base_commit', 'head_commit',
    'implementation_evidence_reference', 'git_diff_reference', 'review_report_reference', 'artifact_path'])
def test_missing_required_information_never_freezes_target(target_case, missing):
    request = request_for(target_case)
    if missing == 'entry':
        request = replace(request, entry=replace(request.entry, entered=False))
    elif missing == 'entry_failed':
        from application.final_approval_entry import EntryFailure
        request = replace(request, entry=replace(request.entry, failures=(EntryFailure('FAILURE', 'not established'),)))
    elif missing in ('implementation_branch', 'base_commit'):
        request = replace(request, entry=with_identity(request.entry, **{missing: ''}))
    elif missing == 'head_commit':
        request = replace(request, entry=replace(request.entry, head_commit=None))
    else:
        request = replace(request, **{missing: None})
    output = execute(request)
    assert not output.succeeded and output.failures
    assert output.artifact is None and output.artifact_hash is None
    assert not target_case[1].exists() and not target_case[4].exists()


@pytest.mark.parametrize('reference', ['implementation_evidence_reference', 'git_diff_reference'])
def test_unavailable_reference_blocks_target(target_case, reference):
    request = request_for(target_case)
    getattr(request, reference).unlink()
    output = execute(request)
    assert not output.succeeded and output.failures
    assert not request.artifact_path.exists()
    assert not request.review_report_reference.exists()


@pytest.mark.parametrize('reference', ['implementation_evidence_reference', 'git_diff_reference'])
def test_reference_content_must_match_existing_entry(target_case, reference):
    request = request_for(target_case)
    path = getattr(request, reference)
    if reference == 'implementation_evidence_reference':
        data = json.loads(path.read_text(encoding='utf-8'))
        data['identity']['implementation_id'] = '11111111-1111-1111-1111-111111111111'
        path.write_text(json.dumps(data), encoding='utf-8')
    else:
        path.write_text('different implementation', encoding='utf-8')
    output = execute(request)
    assert not output.succeeded and output.failures
    assert not request.artifact_path.exists()


@pytest.mark.parametrize('destination', ['artifact_path', 'review_report_reference'])
def test_existing_snapshot_is_not_overwritten(target_case, destination):
    request = request_for(target_case)
    path = getattr(request, destination)
    path.write_bytes(b'previous immutable artifact')
    output = execute(request)
    assert not output.succeeded and output.failures
    assert path.read_bytes() == b'previous immutable artifact'


@pytest.mark.parametrize('destination', ['artifact_path', 'review_report_reference'])
def test_save_failure_retains_failure_and_any_completed_save(target_case, monkeypatch, destination):
    from pathlib import Path
    request = request_for(target_case)
    original = Path.open
    def failing_open(path, mode='r', *args, **kwargs):
        if path == getattr(request, destination) and mode == 'xb':
            raise OSError('snapshot persistence failed')
        return original(path, mode, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', failing_open)
    output = execute(request)
    assert not output.succeeded and output.artifact_hash is None
    assert any('snapshot persistence failed' in f.detail for f in output.failures)
    assert output.saved_paths == ((request.review_report_reference,) if destination == 'artifact_path' else ())


def test_snapshot_bytes_and_hash_are_stable_and_detect_content_changes(target_case):
    from application.final_approval_target import artifact_hash, load_final_approval_target
    request = request_for(target_case)
    first = execute(request)
    assert first.succeeded
    second_path = request.artifact_path.with_name('second_target.json')
    second = execute(replace(request, artifact_path=second_path))
    assert second.succeeded
    assert first.artifact_hash == second.artifact_hash
    assert request.artifact_path.read_bytes() == second_path.read_bytes()
    assert load_final_approval_target(second_path) == first.artifact
    # Simulate external tampering; the production path never updates a snapshot.
    data = json.loads(second_path.read_text(encoding='utf-8'))
    data['head_commit'] = 'c' * 40
    second_path.write_text(json.dumps(data), encoding='utf-8')
    assert artifact_hash(second_path) != first.artifact_hash


def test_target_preserves_saved_identity_and_uses_entry_head(target_case):
    request = request_for(target_case)
    # Target 2 does not substitute or reinterpret independently observed fields.
    entry = replace(request.entry, repository_state=replace(request.entry.repository_state, branch='observation-only'))
    output = execute(replace(request, entry=entry))
    assert output.succeeded
    assert output.artifact.implementation_branch != 'observation-only'
    assert output.artifact.head_commit == entry.head_commit
    assert output.artifact.base_commit != entry.head_commit


def test_target_does_not_operate_outside_final_approval_pending(target_case):
    request = request_for(target_case)
    request.entry.request.state_file.write_text('{"status": "completed"}', encoding='utf-8')
    output = execute(request)
    assert not output.succeeded and output.failures
    assert not request.artifact_path.exists()


def test_missing_review_report_is_not_generated(target_case):
    request = request_for(target_case)
    handoff = request.entry.request.handoff
    continuation = handoff.request.continuation
    continuation = replace(continuation, request=replace(continuation.request, review=replace(continuation.request.review, report=None)))
    handoff = replace(handoff, request=replace(handoff.request, continuation=continuation))
    request = replace(request, entry=replace(request.entry, request=replace(request.entry.request, handoff=handoff)))
    output = execute(request)
    assert not output.succeeded and output.failures
    assert not request.artifact_path.exists()


def test_output_paths_must_not_alias_each_other(target_case):
    request = request_for(target_case)
    output = execute(replace(request, artifact_path=request.review_report_reference))
    assert not output.succeeded and output.failures
    assert not request.review_report_reference.exists()
