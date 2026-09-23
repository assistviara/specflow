import hashlib
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4

import pytest

from application.implementation_evidence import (
    EvidenceBasis, EvidenceChanges, EvidenceCodexSummary, EvidenceDeviations,
    EvidenceIdentity, EvidenceScope, EvidenceVerification, ImplementationEvidence,
)
from application.execution_state_provider import TestState as ActualTestState
from application.repository_state_provider import RepositoryState


@pytest.fixture
def review_case(tmp_path):
    from application.review_input import PrepareReviewInputInput
    from application.prepare_review_input import PrepareReviewInputUseCase

    def write(name, text):
        path = tmp_path / name
        path.write_text(text, encoding="utf-8")
        return path

    spec = write("spec.md", "Required behavior\n")
    plan = write("plan.md", "Approved scope\n")
    prompt = write("prompt.md", "Implement approved scope.\n")
    source = write("source.py", "value = 1\n")
    test = write("test_source.py", "assert value == 1\n")
    diff = write("implementation.diff", "diff --git a/source.py b/source.py\n")
    record = write("record.json", "{}")
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    identity = EvidenceIdentity(
        base_branch="release/base", base_commit="a" * 40,
        implementation_branch="impl/example", evidence_id=uuid4(),
        implementation_id=uuid4(), implementation_kind="INITIAL",
        previous_evidence_id=None, status="COLLECTED",
        created_at=datetime.now(timezone.utc),
    )
    verification = EvidenceVerification(
        test_execution_record_path=record, commands=(),
        tests_created_or_modified=(test.name,), test_commands=("pytest",),
        initial_test_status="COMPLETED", initial_test_result="FAIL",
        target_test_status="COMPLETED", target_test_result="PASS",
        full_test_status="COMPLETED", full_test_result="PASS",
        errors=(), warnings=(), no_tdd_reason=None,
    )
    evidence = ImplementationEvidence(
        identity=identity,
        basis=EvidenceBasis(spec, digest(spec), "spec-approval", plan,
                            digest(plan), "plan-approval", prompt,
                            hashlib.sha256(prompt.read_text(encoding="utf-8").encode("utf-8")).hexdigest()),
        scope=EvidenceScope((source.name, test.name), ("*.py",), ()),
        changes=EvidenceChanges((), (source.name, test.name), (), diff, "changes"),
        verification=verification, deviations=EvidenceDeviations((), (), (), ()),
        codex_summary=EvidenceCodexSummary(None),
    )
    actual = ActualTestState(
        tests_created_or_modified=(test.name,), test_commands=("pytest",),
        initial_test_status="COMPLETED", initial_test_result="FAIL",
        target_test_status="COMPLETED", target_test_result="PASS",
        full_test_status="COMPLETED", full_test_result="PASS",
        errors=(), warnings=(),
    )
    repository = Mock()
    repository.load.return_value = evidence
    repository_state = Mock()
    repository_state.get_state.return_value = RepositoryState(
        identity.implementation_branch, identity.base_commit, " M source.py",
        diff.read_text(encoding="utf-8"), (), (source.name, test.name), (),
    )
    test_provider = Mock()
    test_provider.get_state.return_value = actual
    test_factory = Mock(return_value=test_provider)
    approvals = Mock()
    records = {
        approval_id: dict(approval_id=approval_id, artifact_type=kind,
                          artifact_path=str(path), artifact_hash=digest(path),
                          decision="approved")
        for approval_id, kind, path in (
            ("spec-approval", "specification", spec),
            ("plan-approval", "implementation_plan", plan),
        )
    }
    approvals.get.side_effect = records.get
    request = PrepareReviewInputInput(
        implementation_id=identity.implementation_id, evidence_id=identity.evidence_id,
        repository_path=tmp_path, source_paths=(Path(source.name),),
        test_paths=(Path(test.name),),
    )
    use_case = PrepareReviewInputUseCase(
        evidence_repository=repository, approval_repository=approvals,
        repository_state_provider=repository_state,
        test_state_provider_factory=test_factory,
    )
    return dict(request=request, use_case=use_case, evidence=evidence,
                repository=repository, repository_state=repository_state,
                test_provider=test_provider, test_factory=test_factory,
                actual=actual, records=records, approvals=approvals)


def test_prepares_review_input_preserving_evidence_and_actual_test_result_mismatch(review_case):
    c = review_case
    c["test_provider"].get_state.return_value = replace(c["actual"], full_test_result="FAIL")

    output = c["use_case"].execute(c["request"])

    assert output.review_input is not None
    assert output.missing_information == ()
    assert output.review_input.evidence.verification.full_test_result == "PASS"
    assert output.review_input.test_state.full_test_result == "FAIL"
    mismatch = next(m for m in output.mismatches if m.field == "test.full_test_result")
    assert (mismatch.expected, mismatch.actual) == ("PASS", "FAIL")
    assert output.review_input.sources[0].content == "value = 1\n"
    assert output.review_input.tests[0].content == "assert value == 1\n"
    assert output.review_input.repository_state is c["repository_state"].get_state.return_value
    c["repository"].save.assert_not_called()
    assert c["evidence"].verification.full_test_result == "PASS"


@pytest.mark.parametrize("field", ["specification_path", "implementation_plan_path", "codex_prompt_path"])
def test_missing_required_document_preserves_other_acquired_information(review_case, field):
    c = review_case
    getattr(c["evidence"].basis, field).unlink()
    output = c["use_case"].execute(c["request"])
    assert output.review_input is None
    assert output.missing_information
    assert output.acquisition_errors
    assert output.acquired.evidence is c["evidence"]
    assert output.acquired.test_state == c["actual"]
    assert output.acquired.sources[0].content == "value = 1\n"


@pytest.mark.parametrize("component", ["repository", "repository_state", "test_provider", "approvals"])
def test_required_provider_failure_is_not_an_empty_success(review_case, component):
    c = review_case
    method = {"repository": "load", "repository_state": "get_state",
              "test_provider": "get_state", "approvals": "get"}[component]
    getattr(c[component], method).side_effect = ValueError("unreadable record")
    output = c["use_case"].execute(c["request"])
    assert output.review_input is None
    assert output.missing_information
    assert any("unreadable record" in e for e in output.acquisition_errors)


def test_missing_saved_diff_is_not_an_empty_diff(review_case):
    c = review_case
    c["repository"].load.return_value = replace(
        c["evidence"], changes=replace(c["evidence"].changes, git_diff_path=None),
    )
    output = c["use_case"].execute(c["request"])
    assert output.review_input is None
    assert "saved_diff" in output.missing_information


def test_partial_evidence_and_test_execution_error_are_available_facts(review_case):
    c = review_case
    c["repository"].load.return_value = replace(
        c["evidence"], identity=replace(c["evidence"].identity, status="PARTIAL"),
    )
    c["test_provider"].get_state.return_value = replace(
        c["actual"], full_test_status="ERROR", full_test_result="NONE",
        errors=("test process could not complete",), unavailable_evidence=("warnings",),
    )
    request = replace(c["request"], collection_missing_evidence=("warnings",),
                      collection_inconsistencies=("prior mismatch",))
    output = c["use_case"].execute(request)
    assert output.review_input is not None
    assert output.review_input.test_state.errors == ("test process could not complete",)
    assert output.review_input.request.collection_inconsistencies == ("prior mismatch",)


def test_unavailable_required_test_result_is_not_not_run(review_case):
    c = review_case
    c["test_provider"].get_state.return_value = replace(
        c["actual"], full_test_status="NOT_RUN", full_test_result="NONE",
        unavailable_evidence=("full_test_result",),
    )
    output = c["use_case"].execute(c["request"])
    assert output.review_input is None
    assert "test.full_test_result" in output.missing_information


def test_matching_artifacts_have_no_mismatches_and_bind_saved_identity(review_case):
    c = review_case
    output = c["use_case"].execute(c["request"])
    assert output.review_input is not None
    assert output.mismatches == ()
    c["test_factory"].assert_called_once_with(
        c["evidence"].verification.test_execution_record_path, c["request"].implementation_id,
    )
    c["repository_state"].get_state.assert_called_once_with(c["evidence"].identity.base_commit)


@pytest.mark.parametrize("field", ["implementation_id", "evidence_id"])
def test_readable_identity_mismatch_is_retained(review_case, field):
    c = review_case
    c["repository"].load.return_value = replace(
        c["evidence"], identity=replace(c["evidence"].identity, **{field: uuid4()}),
    )
    output = c["use_case"].execute(c["request"])
    assert output.review_input is not None
    assert any(m.field == f"identity.{field}" for m in output.mismatches)


@pytest.mark.parametrize("label", ["specification", "implementation_plan", "codex_prompt"])
def test_changed_artifact_hash_is_a_mismatch_not_missing_information(review_case, label):
    c = review_case
    path = getattr(c["evidence"].basis, label + "_path")
    path.write_text("changed artifact", encoding="utf-8")
    output = c["use_case"].execute(c["request"])
    assert output.review_input is not None
    assert any(m.field == f"{label}.hash" for m in output.mismatches)
    assert getattr(output.review_input, label).content == "changed artifact"


@pytest.mark.parametrize("field,value", [
    ("approval_id", "another-id"), ("artifact_path", "another.md"),
    ("artifact_hash", "different-hash"), ("artifact_type", "another-type"),
    ("decision", "rejected"),
])
def test_readable_approval_mismatch_is_retained(review_case, field, value):
    c = review_case
    c["records"]["plan-approval"][field] = value
    output = c["use_case"].execute(c["request"])
    assert output.review_input is not None
    assert any(m.field.startswith("implementation_plan.approval") for m in output.mismatches)


@pytest.mark.parametrize("value", [None, {}])
def test_missing_or_malformed_approval_is_required_information_failure(review_case, value):
    c = review_case
    c["records"]["plan-approval"] = value
    output = c["use_case"].execute(c["request"])
    assert output.review_input is None
    assert "implementation_plan.approval" in output.missing_information


@pytest.mark.parametrize("field,value", [
    ("branch", "impl/different"), ("base_commit", "b" * 40),
    ("git_diff", "different diff"), ("created_files", ("unexpected.py",)),
    ("modified_files", ()), ("deleted_files", ("removed.py",)),
])
def test_repository_mismatches_preserve_both_versions(review_case, field, value):
    c = review_case
    c["repository_state"].get_state.return_value = replace(
        c["repository_state"].get_state.return_value, **{field: value},
    )
    output = c["use_case"].execute(c["request"])
    assert output.review_input is not None
    assert any(m.field == f"repository.{field}" for m in output.mismatches)
    assert output.review_input.evidence == c["evidence"]
    assert getattr(output.review_input.repository_state, field) == value


@pytest.mark.parametrize("changes,field", [
    ({"initial_test_result": "PASS"}, "initial_test_result"),
    ({"target_test_status": "ERROR", "target_test_result": "NONE"}, "target_test_status"),
    ({"full_test_status": "NOT_RUN", "full_test_result": "NONE"}, "full_test_status"),
    ({"tests_created_or_modified": ("another_test.py",)}, "tests_created_or_modified"),
    ({"test_commands": ("pytest other",)}, "test_commands"),
    ({"errors": ("execution error",)}, "errors"),
    ({"warnings": ("actual warning",)}, "warnings"),
    ({"no_tdd_reason": "not applicable"}, "no_tdd_reason"),
])
def test_available_test_state_mismatches_do_not_invalidate_input(review_case, changes, field):
    c = review_case
    c["test_provider"].get_state.return_value = replace(c["actual"], **changes)
    output = c["use_case"].execute(c["request"])
    assert output.review_input is not None
    assert any(m.field == f"test.{field}" for m in output.mismatches)


def test_error_sources_are_not_conflated(review_case):
    c = review_case
    c["repository"].load.return_value = replace(
        c["evidence"], verification=replace(c["evidence"].verification,
            errors=("basis acquisition error",), commands=("reported command",)),
    )
    output = c["use_case"].execute(c["request"])
    assert output.review_input is not None
    assert not any(m.field in ("test.errors", "test.commands") for m in output.mismatches)


def test_selected_current_and_unchanged_files_are_read_without_collecting_unrelated_source(review_case):
    c = review_case
    root = c['request'].repository_path
    (root / 'dependency.py').write_text('required unchanged dependency', encoding='utf-8')
    (root / 'unrelated.py').write_text('unrelated', encoding='utf-8')
    (root / 'source.py').write_text('current source', encoding='utf-8')
    request = replace(c['request'], source_paths=(Path('source.py'), Path('dependency.py')))
    output = c['use_case'].execute(request)
    assert output.review_input is not None
    assert [text.content for text in output.review_input.sources] == ['current source', 'required unchanged dependency']


@pytest.mark.parametrize('selection', ['source_paths', 'test_paths'])
def test_empty_selected_file_is_available_but_missing_file_is_not(review_case, selection):
    c = review_case
    path = c['request'].repository_path / getattr(c['request'], selection)[0]
    path.write_bytes(b'')
    output = c['use_case'].execute(c['request'])
    assert output.review_input is not None
    texts = output.review_input.sources if selection == 'source_paths' else output.review_input.tests
    assert texts[0].content == ''
    assert texts[0].sha256 == hashlib.sha256(b'').hexdigest()
    path.unlink()
    output = c['use_case'].execute(c['request'])
    assert output.review_input is None
    assert output.acquired.repository_state.git_diff
    assert any('FileNotFoundError' in error for error in output.acquisition_errors)


def test_selected_reference_outside_repository_is_not_collected(review_case):
    c = review_case
    outside = c['request'].repository_path.parent / 'outside.py'
    outside.write_text('outside', encoding='utf-8')
    output = c['use_case'].execute(replace(c['request'], source_paths=(outside,)))
    assert output.review_input is None
    assert output.acquired.sources == ()
    assert output.acquisition_errors


def test_empty_diff_is_available_information(review_case):
    c = review_case
    c['evidence'].changes.git_diff_path.write_bytes(b'')
    c['repository_state'].get_state.return_value = replace(c['repository_state'].get_state.return_value, git_diff='')
    output = c['use_case'].execute(c['request'])
    assert output.review_input is not None
    assert output.mismatches == ()


@pytest.mark.parametrize('trace_state', ['valid', 'missing', 'changed'])
def test_existing_json_providers_preserve_results_and_report_trace_acquisition_failure(review_case, trace_state):
    from application.execution_record import TestExecutionRecord, TestExecutionResult
    from application.prepare_review_input import PrepareReviewInputUseCase
    from infrastructure.json_implementation_evidence_repository import JsonImplementationEvidenceRepository
    from infrastructure.json_test_execution_record_repository import JsonTestExecutionRecordRepository
    from infrastructure.json_test_state_provider import JsonTestStateProvider

    c = review_case
    root = c['request'].repository_path
    implementation_id = c['request'].implementation_id
    trace = root / f'codex_command_trace_{implementation_id}.jsonl'
    trace.write_bytes(b'')
    record = TestExecutionRecord(
        schema_version='1', implementation_id=implementation_id,
        recorded_at=datetime.now(timezone.utc),
        tests_created_or_modified=c['actual'].tests_created_or_modified,
        test_commands=c['actual'].test_commands,
        initial_test=TestExecutionResult('COMPLETED', 'FAIL'),
        target_test=TestExecutionResult('COMPLETED', 'PASS'),
        full_test=TestExecutionResult('COMPLETED', 'FAIL'),
        errors=(), warnings=(), unavailable_evidence=(), no_tdd_reason=None,
        command_trace_path=trace, command_trace_sha256=hashlib.sha256(trace.read_bytes()).hexdigest(),
    )
    record_path = JsonTestExecutionRecordRepository(root).save(record)
    evidence = replace(c['evidence'], verification=replace(c['evidence'].verification, test_execution_record_path=record_path))
    repository = JsonImplementationEvidenceRepository(root)
    evidence_path = repository.save(evidence)
    before = evidence_path.read_bytes()
    if trace_state == 'missing':
        trace.unlink()
    elif trace_state == 'changed':
        trace.write_bytes(b'changed')
    use_case = PrepareReviewInputUseCase(
        evidence_repository=repository, approval_repository=c['approvals'],
        repository_state_provider=c['repository_state'],
        test_state_provider_factory=lambda path, identity: JsonTestStateProvider(
            record_path=path, expected_implementation_id=identity),
    )
    output = use_case.execute(c['request'])
    assert evidence_path.read_bytes() == before
    assert output.acquired.evidence == evidence
    if trace_state == 'valid':
        assert output.review_input is not None
        assert output.review_input.evidence.verification.full_test_result == 'PASS'
        assert output.review_input.test_state.full_test_result == 'FAIL'
        assert any(m.field == 'test.full_test_result' for m in output.mismatches)
    else:
        assert output.review_input is None
        assert 'test_state' in output.missing_information
        assert output.acquisition_errors


def test_existing_git_provider_supplies_current_diff_and_selected_source(review_case):
    import subprocess
    from application.prepare_review_input import PrepareReviewInputUseCase
    from infrastructure.git_repository_state_provider import GitRepositoryStateProvider

    c = review_case
    root = c['request'].repository_path
    def git(*args):
        return subprocess.run(['git', *args], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
    git('init')
    git('config', 'user.name', 'Test')
    git('config', 'user.email', 'test@example.invalid')
    git('add', '.')
    git('commit', '-m', 'fixture baseline')
    base = git('rev-parse', 'HEAD')
    git('checkout', '-b', 'impl/example')
    (root / 'source.py').write_text('current implementation\n', encoding='utf-8')
    evidence = replace(c['evidence'], identity=replace(c['evidence'].identity, base_commit=base))
    c['repository'].load.return_value = evidence
    use_case = PrepareReviewInputUseCase(
        evidence_repository=c['repository'], approval_repository=c['approvals'],
        repository_state_provider=GitRepositoryStateProvider(root),
        test_state_provider_factory=c['test_factory'],
    )
    output = use_case.execute(c['request'])
    assert output.review_input is not None
    assert output.review_input.sources[0].content == 'current implementation\n'
    assert '+current implementation' in output.review_input.repository_state.git_diff
    assert any(m.field == 'repository.git_diff' for m in output.mismatches)
    assert output.review_input.evidence == evidence


@pytest.mark.parametrize('selection,label', [('source_paths', 'sources'), ('test_paths', 'tests')])
def test_diff_does_not_replace_required_code_selection(review_case, selection, label):
    c = review_case
    output = c['use_case'].execute(replace(c['request'], **{selection: ()}))
    assert output.review_input is None
    assert label in output.missing_information
    assert output.acquired.repository_state.git_diff
