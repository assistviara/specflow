import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from application.collect_implementation_evidence import (
    CollectImplementationEvidenceUseCase,
)
from application.dto import (
    CollectImplementationEvidenceInput,
)
from application.execution_record import (
    TestExecutionRecord as ExecutionRecord,
    TestExecutionResult as ExecutionResult,
)
from application.implementation_evidence import (
    EvidenceScope,
)
from application.implementation_result_parser import (
    ImplementationResult,
)
from infrastructure.git_repository_state_provider import (
    GitRepositoryStateProvider,
)
from infrastructure.json_implementation_evidence_repository import (
    JsonImplementationEvidenceRepository,
)
from infrastructure.json_test_execution_record_repository import (
    JsonTestExecutionRecordRepository,
)
from infrastructure.json_test_state_provider import (
    JsonTestStateProvider,
)


def run_git(
    repository_path: Path,
    *arguments: str,
) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repository_path,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout


def test_collects_evidence_with_real_infrastructure(
    tmp_path: Path,
) -> None:
    repository_path = tmp_path / "repository"
    repository_path.mkdir()

    run_git(repository_path, "init")
    run_git(
        repository_path,
        "config",
        "user.email",
        "test@example.com",
    )
    run_git(
        repository_path,
        "config",
        "user.name",
        "Test User",
    )
    run_git(
        repository_path,
        "checkout",
        "-b",
        "developer",
    )

    application_dir = repository_path / "application"
    tests_dir = repository_path / "tests"
    application_dir.mkdir()
    tests_dir.mkdir()

    application_file = application_dir / "foo.py"
    test_file = tests_dir / "test_foo.py"

    application_file.write_text(
        "def value():\n"
        "    return 1\n",
        encoding="utf-8",
    )
    test_file.write_text(
        "def test_value():\n"
        "    assert 1 == 1\n",
        encoding="utf-8",
    )

    run_git(repository_path, "add", ".")
    run_git(
        repository_path,
        "commit",
        "-m",
        "initial state",
    )
    base_commit = run_git(
        repository_path,
        "rev-parse",
        "HEAD",
    ).strip()

    application_file.write_text(
        "def value():\n"
        "    return 2\n",
        encoding="utf-8",
    )
    test_file.write_text(
        "from application.foo import value\n"
        "\n"
        "\n"
        "def test_value():\n"
        "    assert value() == 2\n",
        encoding="utf-8",
    )

    input_dir = tmp_path / "input"
    input_dir.mkdir()

    specification_path = input_dir / "specification.md"
    specification_path.write_text(
        "approved specification",
        encoding="utf-8",
    )
    plan_path = input_dir / "implementation_plan.md"
    plan_path.write_text(
        "approved implementation plan",
        encoding="utf-8",
    )

    implementation_id = uuid4()
    evidence_dir = tmp_path / "evidence"

    trace_path = (
        evidence_dir
        / f"codex_command_trace_{implementation_id}.jsonl"
    )
    trace_bytes = (
        b'{"event_order":1,"test_phase":"initial"}\n'
        b'{"event_order":2,"test_phase":"target"}\n'
        b'{"event_order":3,"test_phase":"full"}\n'
    )
    evidence_dir.mkdir()
    trace_path.write_bytes(trace_bytes)

    execution_record = ExecutionRecord(
        schema_version="1",
        implementation_id=implementation_id,
        recorded_at=datetime(
            2026,
            9,
            19,
            12,
            0,
            tzinfo=timezone.utc,
        ),
        tests_created_or_modified=(
            "tests/test_foo.py",
        ),
        test_commands=(
            "python -m pytest tests/test_foo.py",
            "python -m pytest",
        ),
        initial_test=ExecutionResult(
            status="COMPLETED",
            result="FAIL",
        ),
        target_test=ExecutionResult(
            status="COMPLETED",
            result="PASS",
        ),
        full_test=ExecutionResult(
            status="COMPLETED",
            result="PASS",
        ),
        errors=(),
        warnings=(),
        unavailable_evidence=(),
        no_tdd_reason=None,
        command_trace_path=trace_path,
        command_trace_sha256=hashlib.sha256(
            trace_bytes
        ).hexdigest(),
    )

    record_path = JsonTestExecutionRecordRepository(
        evidence_dir
    ).save(execution_record)

    evidence_repository = (
        JsonImplementationEvidenceRepository(
            evidence_dir
        )
    )
    use_case = CollectImplementationEvidenceUseCase(
        repository_state_provider=(
            GitRepositoryStateProvider(
                working_directory=repository_path
            )
        ),
        test_state_provider=JsonTestStateProvider(
            record_path=record_path,
            expected_implementation_id=implementation_id,
        ),
        evidence_repository=evidence_repository,
    )

    implementation_result = ImplementationResult(
        implementation_summary=(
            "implemented approved scope"
        ),
        changed_files=(
            "application/foo.py\n"
            "tests/test_foo.py"
        ),
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

    output = use_case.execute(
        CollectImplementationEvidenceInput(
            base_branch="release/baseline",
            test_execution_record_path=record_path,
            implementation_id=implementation_id,
            implementation_kind="INITIAL",
            previous_evidence_id=None,
            specification_path=specification_path,
            specification_approval_id=(
                "spec-approval-001"
            ),
            implementation_plan_path=plan_path,
            implementation_plan_approval_id=(
                "plan-approval-001"
            ),
            codex_prompt_path=(
                input_dir / "codex_prompt.md"
            ),
            codex_prompt="Implement approved scope.",
            implementation_branch="developer",
            base_commit=base_commit,
            implementation_result=(
                implementation_result
            ),
            approved_scope=EvidenceScope(
                target_paths=(
                    "application/**",
                    "tests/**",
                ),
                allowed_changes=(
                    "application/**",
                    "tests/**",
                ),
                forbidden_changes=("core/**",),
            ),
        )
    )

    assert output.success is True
    assert output.status == "COLLECTED"
    assert output.missing_evidence == ()
    assert output.inconsistencies == ()
    assert output.human_approval_required == ()
    assert output.error_message is None

    assert output.evidence_path is not None
    assert output.evidence_path.exists()
    assert output.git_diff_path is not None
    assert output.git_diff_path.exists()

    evidence = output.implementation_evidence
    assert evidence is not None
    assert evidence.identity.implementation_id == (
        implementation_id
    )
    assert evidence.identity.status == "COLLECTED"
    assert evidence.changes.modified_files == (
        "application/foo.py",
        "tests/test_foo.py",
    )
    assert evidence.verification.initial_test_result == (
        "FAIL"
    )
    assert evidence.verification.target_test_result == (
        "PASS"
    )
    assert evidence.verification.full_test_result == (
        "PASS"
    )

    restored = evidence_repository.load(
        output.evidence_id
    )
    assert restored == evidence
    assert restored.identity.base_branch == "release/baseline"
    assert restored.identity.base_commit == base_commit
    assert restored.identity.implementation_branch == "developer"
    assert restored.verification.test_execution_record_path == record_path
    restored_test_state = JsonTestStateProvider(
        record_path=restored.verification.test_execution_record_path,
        expected_implementation_id=restored.identity.implementation_id,
    ).get_state()
    assert restored_test_state.full_test_result == "PASS"

    saved_diff = output.git_diff_path.read_text(
        encoding="utf-8"
    )
    assert "application/foo.py" in saved_diff
    assert "tests/test_foo.py" in saved_diff
