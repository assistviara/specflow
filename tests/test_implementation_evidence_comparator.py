from application.implementation_evidence import EvidenceScope
from application.implementation_evidence_comparator import (
    ImplementationEvidenceComparator,
)
from application.implementation_result_parser import ImplementationResult
from application.repository_state_provider import RepositoryState
from application.execution_state_provider import TestState as State
from application.execution_state_provider import TestState as ExecutionTestState


def make_result(
    changed_files: str = (
        "application/foo.py\n"
        "tests/test_foo.py"
    ),
) -> ImplementationResult:
    return ImplementationResult(
        implementation_summary="completed",
        changed_files=changed_files,
        executed_commands="python -m pytest",
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


def make_repository_state(
    *,
    created_files: tuple[str, ...] = (
        "application/foo.py",
    ),
    modified_files: tuple[str, ...] = (
        "tests/test_foo.py",
    ),
    deleted_files: tuple[str, ...] = (),
    unavailable_evidence: tuple[str, ...] = (),
) -> RepositoryState:
    return RepositoryState(
        branch="developer",
        base_commit="abc123",
        git_status="",
        git_diff="diff",
        created_files=created_files,
        modified_files=modified_files,
        deleted_files=deleted_files,
        unavailable_evidence=unavailable_evidence,
    )


def make_test_state(
    *,
    unavailable_evidence: tuple[str, ...] = (),
) -> State:
    return State(
        tests_created_or_modified=(
            "tests/test_foo.py",
        ),
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
        unavailable_evidence=unavailable_evidence,
    )


def make_scope() -> EvidenceScope:
    return EvidenceScope(
        target_paths=(
            "application/**",
            "tests/**",
        ),
        allowed_changes=(
            "application/**",
            "tests/**",
        ),
        forbidden_changes=(
            "core/**",
        ),
    )


def test_unavailable_evidence_becomes_missing_evidence() -> None:
    comparison = ImplementationEvidenceComparator().compare(
        implementation_result=make_result(),
        repository_state=make_repository_state(
            unavailable_evidence=("git_diff",),
        ),
        test_state=make_test_state(
            unavailable_evidence=(
                "initial_test_result",
            ),
        ),
        scope=make_scope(),
    )

    assert comparison.missing_evidence == (
        "git_diff",
        "initial_test_result",
    )


def test_matching_reported_and_actual_files_has_no_inconsistency() -> None:
    comparison = ImplementationEvidenceComparator().compare(
        implementation_result=make_result(),
        repository_state=make_repository_state(),
        test_state=make_test_state(),
        scope=make_scope(),
    )

    assert comparison.inconsistencies == ()


def test_reported_file_missing_from_actual_changes_is_inconsistency() -> None:
    comparison = ImplementationEvidenceComparator().compare(
        implementation_result=make_result(
            "application/foo.py\n"
            "tests/test_missing.py"
        ),
        repository_state=make_repository_state(),
        test_state=make_test_state(),
        scope=make_scope(),
    )

    assert (
        "reported change not found in actual changes: "
        "tests/test_missing.py"
    ) in comparison.inconsistencies


def test_unreported_actual_change_is_inconsistency() -> None:
    comparison = ImplementationEvidenceComparator().compare(
        implementation_result=make_result(
            "application/foo.py"
        ),
        repository_state=make_repository_state(),
        test_state=make_test_state(),
        scope=make_scope(),
    )

    assert (
        "actual change not reported by Codex: "
        "tests/test_foo.py"
    ) in comparison.inconsistencies


def test_forbidden_actual_change_is_out_of_scope_deviation() -> None:
    comparison = ImplementationEvidenceComparator().compare(
        implementation_result=make_result(
            "application/foo.py\n"
            "core/forbidden.py"
        ),
        repository_state=make_repository_state(
            modified_files=("core/forbidden.py",),
        ),
        test_state=make_test_state(),
        scope=make_scope(),
    )

    assert comparison.out_of_scope_changes == (
        "core/forbidden.py",
    )


def test_change_outside_allowed_patterns_is_unplanned() -> None:
    comparison = ImplementationEvidenceComparator().compare(
        implementation_result=make_result(
            "application/foo.py\n"
            "docs/unplanned.md"
        ),
        repository_state=make_repository_state(
            modified_files=("docs/unplanned.md",),
        ),
        test_state=make_test_state(),
        scope=make_scope(),
    )

    assert comparison.unplanned_changes == (
        "docs/unplanned.md",
    )


def test_blank_lines_and_surrounding_whitespace_are_ignored() -> None:
    comparison = ImplementationEvidenceComparator().compare(
        implementation_result=make_result(
            " application/foo.py \n"
            "\n"
            " tests/test_foo.py "
        ),
        repository_state=make_repository_state(),
        test_state=make_test_state(),
        scope=make_scope(),
    )

    assert comparison.inconsistencies == ()


def test_unstructured_report_item_is_not_interpreted_as_file_path() -> None:
    comparison = ImplementationEvidenceComparator().compare(
        implementation_result=make_result(
            "application周辺を3ファイル修正しました"
        ),
        repository_state=make_repository_state(
            created_files=("application/foo.py",),
            modified_files=("tests/test_foo.py",),
        ),
        test_state=make_test_state(),
        scope=make_scope(),
    )

    assert (
        "reported change not found in actual changes: "
        "application周辺を3ファイル修正しました"
    ) in comparison.inconsistencies

    assert (
        "actual change not reported by Codex: application/foo.py"
    ) in comparison.inconsistencies

    assert (
        "actual change not reported by Codex: tests/test_foo.py"
    ) in comparison.inconsistencies


def test_codex_human_approval_request_is_preserved() -> None:
    result = make_result()
    result = ImplementationResult(
        implementation_summary=result.implementation_summary,
        changed_files=result.changed_files,
        executed_commands=result.executed_commands,
        test_execution_status=result.test_execution_status,
        test_result=result.test_result,
        test_execution_error=result.test_execution_error,
        errors=result.errors,
        warnings=result.warnings,
        incomplete_items=result.incomplete_items,
        human_approval_required="Confirm database migration",
        test_required=result.test_required,
        technical_retry_safe=result.technical_retry_safe,
        technical_retry_operation=result.technical_retry_operation,
    )

    comparison = ImplementationEvidenceComparator().compare(
        implementation_result=result,
        repository_state=make_repository_state(),
        test_state=make_test_state(),
        scope=make_scope(),
    )

    assert comparison.human_approval_required == (
        "Confirm database migration",
    )


def test_codex_none_does_not_create_human_approval_request() -> None:
    comparison = ImplementationEvidenceComparator().compare(
        implementation_result=make_result(),
        repository_state=make_repository_state(),
        test_state=make_test_state(),
        scope=make_scope(),
    )

    assert comparison.human_approval_required == ()


def test_missing_evidence_creates_human_approval_request() -> None:
    comparison = ImplementationEvidenceComparator().compare(
        implementation_result=make_result(),
        repository_state=make_repository_state(
            unavailable_evidence=("git_diff",),
        ),
        test_state=make_test_state(
            unavailable_evidence=("initial_test_result",),
        ),
        scope=make_scope(),
    )

    assert comparison.human_approval_required == (
        "missing evidence requires human judgment: git_diff",
        "missing evidence requires human judgment: initial_test_result",
    )


def test_inconsistency_and_deviation_alone_do_not_require_human_approval() -> None:
    comparison = ImplementationEvidenceComparator().compare(
        implementation_result=make_result(
            "tests/test_missing.py\n"
            "core/forbidden.py"
        ),
        repository_state=make_repository_state(
            created_files=("application/foo.py",),
            modified_files=("core/forbidden.py",),
        ),
        test_state=make_test_state(),
        scope=make_scope(),
    )

    assert comparison.inconsistencies != ()
    assert comparison.out_of_scope_changes == (
        "core/forbidden.py",
    )
    assert comparison.human_approval_required == ()


def test_compare_records_missing_evidence_when_scope_is_unavailable() -> None:
    implementation_result = ImplementationResult(
        implementation_summary="done",
        changed_files="application/example.py",
        executed_commands="python -m pytest",
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

    repository_state = RepositoryState(
        branch="developer",
        base_commit="abc123",
        git_status="",
        git_diff="diff content",
        created_files=("application/example.py",),
        modified_files=(),
        deleted_files=(),
    )

    test_state = ExecutionTestState(
        tests_created_or_modified=("tests/test_example.py",),
        test_commands=("python -m pytest",),
        initial_test_status="COMPLETED",
        initial_test_result="FAIL",
        target_test_status="COMPLETED",
        target_test_result="PASS",
        full_test_status="COMPLETED",
        full_test_result="PASS",
        errors=(),
        warnings=(),
    )

    comparison = ImplementationEvidenceComparator().compare(
        implementation_result=implementation_result,
        repository_state=repository_state,
        test_state=test_state,
        scope=None,
    )

    assert "approved scope unavailable" in comparison.missing_evidence
    assert comparison.out_of_scope_changes == ()
    assert comparison.unplanned_changes == ()
    assert comparison.inconsistencies == ()
    assert (
        "missing evidence requires human judgment: approved scope unavailable"
        in comparison.human_approval_required
    )
