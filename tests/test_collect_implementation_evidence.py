from pathlib import Path
from uuid import UUID, uuid4

import pytest

from application.collect_implementation_evidence import (
    CollectImplementationEvidenceUseCase,
)
from application.dto import CollectImplementationEvidenceInput
from application.execution_state_provider import TestState as ExecutionTestState
from application.implementation_evidence import EvidenceScope
from application.implementation_result_parser import ImplementationResult
from application.repository_state_provider import RepositoryState


class FakeRepositoryStateProvider:
    def __init__(self, state):
        self.state = state
        self.requested_base_commit = None

    def get_state(self, base_commit):
        self.requested_base_commit = base_commit
        return self.state


class FakeTestStateProvider:
    def __init__(self, state):
        self.state = state
        self.called = False

    def get_state(self):
        self.called = True
        return self.state


class RecordingEvidenceRepository:
    def __init__(self):
        self.calls = []
        self.saved_diff = None
        self.saved_evidence = None

    def save_diff(self, evidence_id, diff):
        self.calls.append("save_diff")
        self.saved_diff = (evidence_id, diff)
        return Path(
            f"evidence/implementation_{evidence_id}.diff"
        )

    def save(self, evidence):
        self.calls.append("save")
        self.saved_evidence = evidence
        return Path(
            "evidence/"
            f"implementation_{evidence.identity.evidence_id}.json"
        )

    def exists(self, evidence_id):
        return False

    def load(self, evidence_id):
        raise FileNotFoundError(evidence_id)


def make_result():
    return ImplementationResult(
        implementation_summary="implemented approved scope",
        changed_files="application/foo.py\ntests/test_foo.py",
        executed_commands=(
            "python -m pytest tests/test_foo.py\n"
            "python -m pytest"
        ),
        test_execution_status="COMPLETED",
        test_result="PASS",
        test_execution_error="NONE",
        errors="NONE",
        warnings="NONE",
        incomplete_items="NONE",
        human_approval_required="NONE",
        test_required=True,
        technical_retry_safe=False,
        technical_retry_operation=None,
    )


def test_collects_and_persists_complete_implementation_evidence(
    tmp_path,
):
    specification_path = tmp_path / "specification.md"
    specification_path.write_text(
        "approved specification",
        encoding="utf-8",
    )

    plan_path = tmp_path / "plan.md"
    plan_path.write_text(
        "approved implementation plan",
        encoding="utf-8",
    )

    repository_state = RepositoryState(
        branch="developer",
        base_commit="abc123",
        git_status=" M application/foo.py",
        git_diff="diff --git a/foo.py b/foo.py\n",
        created_files=("application/foo.py",),
        modified_files=("tests/test_foo.py",),
        deleted_files=(),
        unavailable_evidence=(),
    )

    test_state = ExecutionTestState(
        tests_created_or_modified=("tests/test_foo.py",),
        test_commands=(
            "python -m pytest tests/test_foo.py",
        ),
        initial_test_status="COMPLETED",
        initial_test_result="FAIL",
        target_test_status="COMPLETED",
        target_test_result="PASS",
        full_test_status="COMPLETED",
        full_test_result="PASS",
        errors=(),
        warnings=(),
        unavailable_evidence=(),
        no_tdd_reason=None,
    )

    repository_provider = FakeRepositoryStateProvider(
        repository_state
    )
    test_provider = FakeTestStateProvider(test_state)
    evidence_repository = RecordingEvidenceRepository()

    use_case = CollectImplementationEvidenceUseCase(
        repository_state_provider=repository_provider,
        test_state_provider=test_provider,
        evidence_repository=evidence_repository,
    )

    implementation_id = uuid4()

    output = use_case.execute(
        CollectImplementationEvidenceInput(
            implementation_id=implementation_id,
            implementation_kind="INITIAL",
            previous_evidence_id=None,
            specification_path=specification_path,
            specification_approval_id="spec-approval-001",
            implementation_plan_path=plan_path,
            implementation_plan_approval_id="plan-approval-001",
            codex_prompt_path=tmp_path / "codex_prompt.md",
            codex_prompt="Implement approved scope.",
            implementation_branch="developer",
            base_commit="abc123",
            implementation_result=make_result(),
            approved_scope=EvidenceScope(
                target_paths=("application/**", "tests/**"),
                allowed_changes=("application/**", "tests/**"),
                forbidden_changes=("core/**",),
            ),
        )
    )

    assert output.success is True
    assert isinstance(output.evidence_id, UUID)
    assert output.implementation_id == implementation_id
    assert output.status == "COLLECTED"
    assert output.missing_evidence == ()
    assert output.inconsistencies == ()
    assert output.human_approval_required == ()
    assert output.error_message is None

    evidence = output.implementation_evidence
    assert evidence is not None
    assert evidence.identity.evidence_id == output.evidence_id
    assert evidence.identity.status == "COLLECTED"
    assert evidence.identity.created_at.tzinfo is not None
    assert evidence.identity.created_at.utcoffset() is not None

    assert evidence.changes.created_files == (
        "application/foo.py",
    )
    assert evidence.changes.modified_files == (
        "tests/test_foo.py",
    )
    assert evidence.changes.git_diff_path == output.git_diff_path
    assert evidence.changes.change_summary == (
        "implemented approved scope"
    )

    assert evidence.verification.commands == (
        "python -m pytest tests/test_foo.py",
        "python -m pytest",
    )
    assert evidence.verification.test_commands == (
        "python -m pytest tests/test_foo.py",
    )
    assert evidence.deviations.unfinished_items == ()

    assert repository_provider.requested_base_commit == "abc123"
    assert test_provider.called is True
    assert evidence_repository.calls == ["save_diff", "save"]
    assert evidence_repository.saved_diff == (
        output.evidence_id,
        repository_state.git_diff,
    )
    assert evidence_repository.saved_evidence is evidence
    assert output.evidence_path == Path(
        f"evidence/implementation_{output.evidence_id}.json"
    )



class RaisingRepositoryStateProvider:
    def get_state(self, base_commit):
        raise RuntimeError("repository unavailable")


class RaisingTestStateProvider:
    def get_state(self):
        raise RuntimeError("test state unavailable")


def make_failure_input(tmp_path):
    specification_path = tmp_path / "failure_specification.md"
    specification_path.write_text(
        "approved specification",
        encoding="utf-8",
    )

    plan_path = tmp_path / "failure_plan.md"
    plan_path.write_text(
        "approved implementation plan",
        encoding="utf-8",
    )

    return CollectImplementationEvidenceInput(
        implementation_id=uuid4(),
        implementation_kind="INITIAL",
        previous_evidence_id=None,
        specification_path=specification_path,
        specification_approval_id="spec-approval-001",
        implementation_plan_path=plan_path,
        implementation_plan_approval_id="plan-approval-001",
        codex_prompt_path=tmp_path / "codex_prompt.md",
        codex_prompt="Implement approved scope.",
        implementation_branch="developer",
        base_commit="abc123",
        implementation_result=make_result(),
        approved_scope=EvidenceScope(
            target_paths=("application/**", "tests/**"),
            allowed_changes=("application/**", "tests/**"),
            forbidden_changes=("core/**",),
        ),
    )


def assert_provider_failure_output(
    output,
    input_dto,
    expected_error,
):
    assert output.success is False
    assert isinstance(output.evidence_id, UUID)
    assert output.implementation_id == input_dto.implementation_id
    assert output.implementation_evidence is None
    assert output.evidence_path is None
    assert output.git_diff_path is None
    assert output.status is None
    assert output.missing_evidence == ()
    assert output.inconsistencies == ()
    assert output.human_approval_required == ()
    assert output.error_message == expected_error


def test_repository_provider_exception_returns_failure(
    tmp_path,
):
    test_provider = FakeTestStateProvider(
        ExecutionTestState(
            tests_created_or_modified=(),
            test_commands=(),
            initial_test_status="NOT_RUN",
            initial_test_result="NONE",
            target_test_status="NOT_RUN",
            target_test_result="NONE",
            full_test_status="NOT_RUN",
            full_test_result="NONE",
            errors=(),
            warnings=(),
        )
    )
    evidence_repository = RecordingEvidenceRepository()
    input_dto = make_failure_input(tmp_path)

    use_case = CollectImplementationEvidenceUseCase(
        repository_state_provider=(
            RaisingRepositoryStateProvider()
        ),
        test_state_provider=test_provider,
        evidence_repository=evidence_repository,
    )

    output = use_case.execute(input_dto)

    assert_provider_failure_output(
        output,
        input_dto,
        (
            "RepositoryStateProvider failed: "
            "repository unavailable"
        ),
    )
    assert test_provider.called is False
    assert evidence_repository.calls == []


def test_test_provider_exception_returns_failure(
    tmp_path,
):
    repository_provider = FakeRepositoryStateProvider(
        RepositoryState(
            branch="developer",
            base_commit="abc123",
            git_status="",
            git_diff="diff",
            created_files=(),
            modified_files=(),
            deleted_files=(),
        )
    )
    evidence_repository = RecordingEvidenceRepository()
    input_dto = make_failure_input(tmp_path)

    use_case = CollectImplementationEvidenceUseCase(
        repository_state_provider=repository_provider,
        test_state_provider=RaisingTestStateProvider(),
        evidence_repository=evidence_repository,
    )

    output = use_case.execute(input_dto)

    assert_provider_failure_output(
        output,
        input_dto,
        "TestStateProvider failed: test state unavailable",
    )
    assert repository_provider.requested_base_commit == "abc123"
    assert evidence_repository.calls == []



class ProviderMustNotRun:
    def get_state(self, *args):
        raise AssertionError(
            "Provider must not run before generation validation."
        )


class TrackingEvidenceRepository(RecordingEvidenceRepository):
    def __init__(self, existing_ids=()):
        super().__init__()
        self.existing_ids = set(existing_ids)
        self.checked_ids = []

    def exists(self, evidence_id):
        self.checked_ids.append(evidence_id)
        return evidence_id in self.existing_ids


@pytest.mark.parametrize(
    (
        "implementation_kind",
        "has_previous_evidence",
        "expected_error",
    ),
    (
        (
            "INITIAL",
            True,
            (
                "INITIAL evidence must not have "
                "previous_evidence_id"
            ),
        ),
        (
            "CORRECTION",
            False,
            (
                "CORRECTION evidence requires "
                "previous_evidence_id"
            ),
        ),
        (
            "REIMPLEMENTATION",
            False,
            (
                "REIMPLEMENTATION evidence requires "
                "previous_evidence_id"
            ),
        ),
    ),
)
def test_invalid_generation_combination_returns_failure(
    tmp_path,
    implementation_kind,
    has_previous_evidence,
    expected_error,
):
    input_dto = make_failure_input(tmp_path)
    previous_evidence_id = (
        uuid4() if has_previous_evidence else None
    )
    input_dto = CollectImplementationEvidenceInput(
        implementation_id=input_dto.implementation_id,
        implementation_kind=implementation_kind,
        previous_evidence_id=previous_evidence_id,
        specification_path=input_dto.specification_path,
        specification_approval_id=(
            input_dto.specification_approval_id
        ),
        implementation_plan_path=(
            input_dto.implementation_plan_path
        ),
        implementation_plan_approval_id=(
            input_dto.implementation_plan_approval_id
        ),
        codex_prompt_path=input_dto.codex_prompt_path,
        codex_prompt=input_dto.codex_prompt,
        implementation_branch=input_dto.implementation_branch,
        base_commit=input_dto.base_commit,
        implementation_result=input_dto.implementation_result,
        approved_scope=input_dto.approved_scope,
    )
    evidence_repository = TrackingEvidenceRepository()

    use_case = CollectImplementationEvidenceUseCase(
        repository_state_provider=ProviderMustNotRun(),
        test_state_provider=ProviderMustNotRun(),
        evidence_repository=evidence_repository,
    )

    output = use_case.execute(input_dto)

    assert_provider_failure_output(
        output,
        input_dto,
        expected_error,
    )
    assert evidence_repository.checked_ids == []
    assert evidence_repository.calls == []


def test_nonexistent_previous_evidence_returns_failure(
    tmp_path,
):
    input_dto = make_failure_input(tmp_path)
    previous_evidence_id = uuid4()
    input_dto = CollectImplementationEvidenceInput(
        implementation_id=input_dto.implementation_id,
        implementation_kind="CORRECTION",
        previous_evidence_id=previous_evidence_id,
        specification_path=input_dto.specification_path,
        specification_approval_id=(
            input_dto.specification_approval_id
        ),
        implementation_plan_path=(
            input_dto.implementation_plan_path
        ),
        implementation_plan_approval_id=(
            input_dto.implementation_plan_approval_id
        ),
        codex_prompt_path=input_dto.codex_prompt_path,
        codex_prompt=input_dto.codex_prompt,
        implementation_branch=input_dto.implementation_branch,
        base_commit=input_dto.base_commit,
        implementation_result=input_dto.implementation_result,
        approved_scope=input_dto.approved_scope,
    )
    evidence_repository = TrackingEvidenceRepository()

    use_case = CollectImplementationEvidenceUseCase(
        repository_state_provider=ProviderMustNotRun(),
        test_state_provider=ProviderMustNotRun(),
        evidence_repository=evidence_repository,
    )

    output = use_case.execute(input_dto)

    assert_provider_failure_output(
        output,
        input_dto,
        (
            "previous evidence does not exist: "
            f"{previous_evidence_id}"
        ),
    )
    assert evidence_repository.checked_ids == [
        previous_evidence_id
    ]
    assert evidence_repository.calls == []


def test_current_evidence_self_reference_returns_failure(
    tmp_path,
    monkeypatch,
):
    evidence_id = uuid4()
    input_dto = make_failure_input(tmp_path)
    input_dto = CollectImplementationEvidenceInput(
        implementation_id=input_dto.implementation_id,
        implementation_kind="CORRECTION",
        previous_evidence_id=evidence_id,
        specification_path=input_dto.specification_path,
        specification_approval_id=(
            input_dto.specification_approval_id
        ),
        implementation_plan_path=(
            input_dto.implementation_plan_path
        ),
        implementation_plan_approval_id=(
            input_dto.implementation_plan_approval_id
        ),
        codex_prompt_path=input_dto.codex_prompt_path,
        codex_prompt=input_dto.codex_prompt,
        implementation_branch=input_dto.implementation_branch,
        base_commit=input_dto.base_commit,
        implementation_result=input_dto.implementation_result,
        approved_scope=input_dto.approved_scope,
    )
    evidence_repository = TrackingEvidenceRepository(
        existing_ids=(evidence_id,)
    )

    monkeypatch.setattr(
        "application.collect_implementation_evidence.uuid4",
        lambda: evidence_id,
    )

    use_case = CollectImplementationEvidenceUseCase(
        repository_state_provider=ProviderMustNotRun(),
        test_state_provider=ProviderMustNotRun(),
        evidence_repository=evidence_repository,
    )

    output = use_case.execute(input_dto)

    assert_provider_failure_output(
        output,
        input_dto,
        (
            "previous_evidence_id must not reference "
            "current evidence_id"
        ),
    )
    assert evidence_repository.checked_ids == []
    assert evidence_repository.calls == []
