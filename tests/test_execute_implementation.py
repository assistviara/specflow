from pathlib import Path
import subprocess

from application.dto import ExecuteImplementationInput
from application.execute_implementation import ExecuteImplementationUseCase
from core.approval_record_service import (
    build_approval_record_from_artifact,
)


def initialize_clean_git_repository(
    working_directory: Path,
) -> None:
    subprocess.run(
        ["git", "init"],
        cwd=working_directory,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "specflow@example.com"],
        cwd=working_directory,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "SpecFlow Test"],
        cwd=working_directory,
        check=True,
    )
    subprocess.run(
        ["git", "add", "."],
        cwd=working_directory,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "test baseline"],
        cwd=working_directory,
        check=True,
        capture_output=True,
        text=True,
    )


class FakeApprovalRecordRepository:
    def __init__(self, records: dict[str, dict]) -> None:
        self._records = records

    def get(self, approval_id: str) -> dict | None:
        return self._records.get(approval_id)


class SuccessfulCodexImplementationAdapter:
    def __init__(self) -> None:
        self.called = False

    def run(
        self,
        *,
        prompt: str,
        working_directory: Path,
    ) -> str:
        self.called = True

        return """## Implementation Summary
TEST_REQUIRED: YES
Approved scope implementation completed.

## Changed Files
application/example.py

## Executed Commands
python -m pytest -q tests/test_example.py

## Test Execution Status
COMPLETED

## Test Result
PASS

## Test Execution Error
TECHNICAL_RETRY_SAFE: NO
TECHNICAL_RETRY_OPERATION: NONE

## Errors
NONE

## Warnings
NONE

## Incomplete Items
NONE

## Human Approval Required
NONE
"""


def test_successful_implementation_moves_to_implementation_completed(
    tmp_path,
) -> None:
    specification_path = tmp_path / "specification.md"
    specification_path.write_text(
        "approved specification",
        encoding="utf-8",
    )

    implementation_plan_path = tmp_path / "implementation_plan.md"
    implementation_plan_path.write_text(
        "approved implementation plan",
        encoding="utf-8",
    )

    specification_record = build_approval_record_from_artifact(
        approval_id="spec-approval-001",
        artifact_type="specification",
        artifact_path=str(specification_path),
        decision="approved",
        approved_at="2026-09-09T10:00:00+09:00",
        comment="Specification approved.",
    )

    plan_record = build_approval_record_from_artifact(
        approval_id="plan-approval-001",
        artifact_type="implementation_plan",
        artifact_path=str(implementation_plan_path),
        decision="approved",
        approved_at="2026-09-09T10:01:00+09:00",
        comment="Implementation Plan approved.",
    )

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"status": "implementation_ready"}',
        encoding="utf-8",
    )

    adapter = SuccessfulCodexImplementationAdapter()

    use_case = ExecuteImplementationUseCase(
        approval_repository=FakeApprovalRecordRepository(
            {
                "spec-approval-001": specification_record,
                "plan-approval-001": plan_record,
            }
        ),
        implementation_adapter=adapter,
    )

    output = use_case.execute(
        ExecuteImplementationInput(
            specification_path=specification_path,
            specification_approval_id="spec-approval-001",
            implementation_plan_path=implementation_plan_path,
            implementation_plan_approval_id="plan-approval-001",
            codex_prompt="implement approved scope",
            codex_prompt_specification_path=specification_path,
            codex_prompt_implementation_plan_path=implementation_plan_path,
            implementation_branch="developer",
            base_commit="abc123",
            working_directory=tmp_path,
            state_file=state_file,
            state_history_dir=tmp_path / "state_history",
        )
    )

    assert adapter.called is True

    assert output.success is True
    assert output.current_state == "implementation_completed"
    assert output.technical_retry_required is False
    assert output.critical_change_required is False
    assert output.stop_reason is None
    assert output.error_message is None

    assert output.implementation_result is not None
    assert output.implementation_result.test_execution_status == "COMPLETED"
    assert output.implementation_result.test_result == "PASS"

    assert (
        output.specification_approval_validation_result.is_valid
        is True
    )
    assert (
        output.implementation_plan_approval_validation_result.is_valid
        is True
    )

    current_state = state_file.read_text(encoding="utf-8")
    assert '"status": "implementation_completed"' in current_state


def test_invalid_specification_approval_blocks_implementation(
    tmp_path,
) -> None:
    specification_path = tmp_path / "specification.md"
    specification_path.write_text(
        "approved specification",
        encoding="utf-8",
    )

    implementation_plan_path = tmp_path / "implementation_plan.md"
    implementation_plan_path.write_text(
        "approved implementation plan",
        encoding="utf-8",
    )

    specification_record = build_approval_record_from_artifact(
        approval_id="spec-approval-001",
        artifact_type="specification",
        artifact_path=str(specification_path),
        decision="approved",
        approved_at="2026-09-09T10:00:00+09:00",
        comment="Specification approved.",
    )

    plan_record = build_approval_record_from_artifact(
        approval_id="plan-approval-001",
        artifact_type="implementation_plan",
        artifact_path=str(implementation_plan_path),
        decision="approved",
        approved_at="2026-09-09T10:01:00+09:00",
        comment="Implementation Plan approved.",
    )

    specification_path.write_text(
        "modified specification",
        encoding="utf-8",
    )

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"status": "implementation_ready"}',
        encoding="utf-8",
    )

    class AdapterMustNotRun:
        def run(self, **kwargs):
            raise AssertionError(
                "Implementation must not start "
                "when approval is invalid."
            )

    use_case = ExecuteImplementationUseCase(
        approval_repository=FakeApprovalRecordRepository(
            {
                "spec-approval-001": specification_record,
                "plan-approval-001": plan_record,
            }
        ),
        implementation_adapter=AdapterMustNotRun(),
    )

    output = use_case.execute(
        ExecuteImplementationInput(
            specification_path=specification_path,
            specification_approval_id="spec-approval-001",
            implementation_plan_path=implementation_plan_path,
            implementation_plan_approval_id="plan-approval-001",
            codex_prompt="implement approved scope",
            codex_prompt_specification_path=specification_path,
            codex_prompt_implementation_plan_path=implementation_plan_path,
            implementation_branch="developer",
            base_commit="abc123",
            working_directory=tmp_path,
            state_file=state_file,
            state_history_dir=tmp_path / "state_history",
        )
    )

    assert (
        output.specification_approval_validation_result.is_valid
        is False
    )
    assert (
        output.implementation_plan_approval_validation_result.is_valid
        is True
    )
    assert output.success is False
    assert output.implementation_result is None
    assert output.current_state == "implementation_ready"
    assert output.technical_retry_required is False
    assert output.critical_change_required is False
    assert output.stop_reason == "Approval validation failed."

    current_state = state_file.read_text(encoding="utf-8")
    assert '"status": "implementation_ready"' in current_state


def test_invalid_implementation_plan_approval_blocks_implementation(
    tmp_path,
) -> None:
    specification_path = tmp_path / "specification.md"
    specification_path.write_text(
        "approved specification",
        encoding="utf-8",
    )

    implementation_plan_path = tmp_path / "implementation_plan.md"
    implementation_plan_path.write_text(
        "approved implementation plan",
        encoding="utf-8",
    )

    specification_record = build_approval_record_from_artifact(
        approval_id="spec-approval-001",
        artifact_type="specification",
        artifact_path=str(specification_path),
        decision="approved",
        approved_at="2026-09-09T10:00:00+09:00",
        comment="Specification approved.",
    )

    plan_record = build_approval_record_from_artifact(
        approval_id="plan-approval-001",
        artifact_type="implementation_plan",
        artifact_path=str(implementation_plan_path),
        decision="approved",
        approved_at="2026-09-09T10:01:00+09:00",
        comment="Implementation Plan approved.",
    )

    implementation_plan_path.write_text(
        "modified implementation plan",
        encoding="utf-8",
    )

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"status": "implementation_ready"}',
        encoding="utf-8",
    )

    class AdapterMustNotRun:
        def run(self, **kwargs):
            raise AssertionError(
                "Implementation must not start "
                "when approval is invalid."
            )

    use_case = ExecuteImplementationUseCase(
        approval_repository=FakeApprovalRecordRepository(
            {
                "spec-approval-001": specification_record,
                "plan-approval-001": plan_record,
            }
        ),
        implementation_adapter=AdapterMustNotRun(),
    )

    output = use_case.execute(
        ExecuteImplementationInput(
            specification_path=specification_path,
            specification_approval_id="spec-approval-001",
            implementation_plan_path=implementation_plan_path,
            implementation_plan_approval_id="plan-approval-001",
            codex_prompt="implement approved scope",
            codex_prompt_specification_path=specification_path,
            codex_prompt_implementation_plan_path=implementation_plan_path,
            implementation_branch="developer",
            base_commit="abc123",
            working_directory=tmp_path,
            state_file=state_file,
            state_history_dir=tmp_path / "state_history",
        )
    )

    assert (
        output.specification_approval_validation_result.is_valid
        is True
    )
    assert (
        output.implementation_plan_approval_validation_result.is_valid
        is False
    )
    assert output.success is False
    assert output.implementation_result is None
    assert output.current_state == "implementation_ready"
    assert output.technical_retry_required is False
    assert output.critical_change_required is False
    assert output.stop_reason == "Approval validation failed."

    current_state = state_file.read_text(encoding="utf-8")
    assert '"status": "implementation_ready"' in current_state


def test_codex_prompt_path_mismatch_blocks_implementation(
    tmp_path,
) -> None:
    specification_path = tmp_path / "specification.md"
    specification_path.write_text(
        "approved specification",
        encoding="utf-8",
    )

    implementation_plan_path = tmp_path / "implementation_plan.md"
    implementation_plan_path.write_text(
        "approved implementation plan",
        encoding="utf-8",
    )

    specification_record = build_approval_record_from_artifact(
        approval_id="spec-approval-001",
        artifact_type="specification",
        artifact_path=str(specification_path),
        decision="approved",
        approved_at="2026-09-09T10:00:00+09:00",
        comment="Specification approved.",
    )

    plan_record = build_approval_record_from_artifact(
        approval_id="plan-approval-001",
        artifact_type="implementation_plan",
        artifact_path=str(implementation_plan_path),
        decision="approved",
        approved_at="2026-09-09T10:01:00+09:00",
        comment="Implementation Plan approved.",
    )

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"status": "implementation_ready"}',
        encoding="utf-8",
    )

    class AdapterMustNotRun:
        def run(self, **kwargs):
            raise AssertionError(
                "Implementation must not start "
                "when Codex Prompt correspondence is invalid."
            )

    use_case = ExecuteImplementationUseCase(
        approval_repository=FakeApprovalRecordRepository(
            {
                "spec-approval-001": specification_record,
                "plan-approval-001": plan_record,
            }
        ),
        implementation_adapter=AdapterMustNotRun(),
    )

    output = use_case.execute(
        ExecuteImplementationInput(
            specification_path=specification_path,
            specification_approval_id="spec-approval-001",
            implementation_plan_path=implementation_plan_path,
            implementation_plan_approval_id="plan-approval-001",
            codex_prompt="implement approved scope",
            codex_prompt_specification_path=(
                tmp_path / "different_specification.md"
            ),
            codex_prompt_implementation_plan_path=implementation_plan_path,
            implementation_branch="developer",
            base_commit="abc123",
            working_directory=tmp_path,
            state_file=state_file,
            state_history_dir=tmp_path / "state_history",
        )
    )

    assert output.success is False
    assert output.implementation_result is None
    assert output.current_state == "implementation_ready"
    assert output.technical_retry_required is False
    assert output.critical_change_required is False
    assert output.stop_reason == "Codex Prompt correspondence validation failed."

    current_state = state_file.read_text(encoding="utf-8")
    assert '"status": "implementation_ready"' in current_state


def test_completed_fail_still_moves_to_implementation_completed(
    tmp_path,
) -> None:
    specification_path = tmp_path / "specification.md"
    specification_path.write_text(
        "approved specification",
        encoding="utf-8",
    )

    implementation_plan_path = tmp_path / "implementation_plan.md"
    implementation_plan_path.write_text(
        "approved implementation plan",
        encoding="utf-8",
    )

    specification_record = build_approval_record_from_artifact(
        approval_id="spec-approval-001",
        artifact_type="specification",
        artifact_path=str(specification_path),
        decision="approved",
        approved_at="2026-09-09T10:00:00+09:00",
        comment="Specification approved.",
    )

    plan_record = build_approval_record_from_artifact(
        approval_id="plan-approval-001",
        artifact_type="implementation_plan",
        artifact_path=str(implementation_plan_path),
        decision="approved",
        approved_at="2026-09-09T10:01:00+09:00",
        comment="Implementation Plan approved.",
    )

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"status": "implementation_ready"}',
        encoding="utf-8",
    )

    class FailingTestsAdapter:
        def run(
            self,
            *,
            prompt: str,
            working_directory: Path,
        ) -> str:
            return """## Implementation Summary
TEST_REQUIRED: YES
Implementation completed, but tests failed.

## Changed Files
application/example.py

## Executed Commands
python -m pytest -q tests/test_example.py

## Test Execution Status
COMPLETED

## Test Result
FAIL

## Test Execution Error
TECHNICAL_RETRY_SAFE: NO
TECHNICAL_RETRY_OPERATION: NONE

## Errors
NONE

## Warnings
NONE

## Incomplete Items
NONE

## Human Approval Required
NONE
"""

    use_case = ExecuteImplementationUseCase(
        approval_repository=FakeApprovalRecordRepository(
            {
                "spec-approval-001": specification_record,
                "plan-approval-001": plan_record,
            }
        ),
        implementation_adapter=FailingTestsAdapter(),
    )

    output = use_case.execute(
        ExecuteImplementationInput(
            specification_path=specification_path,
            specification_approval_id="spec-approval-001",
            implementation_plan_path=implementation_plan_path,
            implementation_plan_approval_id="plan-approval-001",
            codex_prompt="implement approved scope",
            codex_prompt_specification_path=specification_path,
            codex_prompt_implementation_plan_path=implementation_plan_path,
            implementation_branch="developer",
            base_commit="abc123",
            working_directory=tmp_path,
            state_file=state_file,
            state_history_dir=tmp_path / "state_history",
        )
    )

    assert output.success is True
    assert output.current_state == "implementation_completed"
    assert output.technical_retry_required is False
    assert output.critical_change_required is False
    assert output.implementation_result is not None
    assert output.implementation_result.test_result == "FAIL"

    current_state = state_file.read_text(encoding="utf-8")
    assert '"status": "implementation_completed"' in current_state


def test_test_execution_error_moves_to_implementation_failed(
    tmp_path,
) -> None:
    specification_path = tmp_path / "specification.md"
    specification_path.write_text(
        "approved specification",
        encoding="utf-8",
    )

    implementation_plan_path = tmp_path / "implementation_plan.md"
    implementation_plan_path.write_text(
        "approved implementation plan",
        encoding="utf-8",
    )

    specification_record = build_approval_record_from_artifact(
        approval_id="spec-approval-001",
        artifact_type="specification",
        artifact_path=str(specification_path),
        decision="approved",
        approved_at="2026-09-09T10:00:00+09:00",
        comment="Specification approved.",
    )

    plan_record = build_approval_record_from_artifact(
        approval_id="plan-approval-001",
        artifact_type="implementation_plan",
        artifact_path=str(implementation_plan_path),
        decision="approved",
        approved_at="2026-09-09T10:01:00+09:00",
        comment="Implementation Plan approved.",
    )

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"status": "implementation_ready"}',
        encoding="utf-8",
    )

    class TechnicalErrorAdapter:
        def run(
            self,
            *,
            prompt: str,
            working_directory: Path,
        ) -> str:
            return """## Implementation Summary
TEST_REQUIRED: YES
Implementation could not complete because test execution failed.

## Changed Files
NONE

## Executed Commands
python -m pytest -q tests/test_example.py

## Test Execution Status
ERROR

## Test Result
NONE

## Test Execution Error
TECHNICAL_RETRY_SAFE: NO
TECHNICAL_RETRY_OPERATION: NONE
pytest could not start.

## Errors
Test execution error.

## Warnings
NONE

## Incomplete Items
NONE

## Human Approval Required
NONE
"""

    use_case = ExecuteImplementationUseCase(
        approval_repository=FakeApprovalRecordRepository(
            {
                "spec-approval-001": specification_record,
                "plan-approval-001": plan_record,
            }
        ),
        implementation_adapter=TechnicalErrorAdapter(),
    )

    output = use_case.execute(
        ExecuteImplementationInput(
            specification_path=specification_path,
            specification_approval_id="spec-approval-001",
            implementation_plan_path=implementation_plan_path,
            implementation_plan_approval_id="plan-approval-001",
            codex_prompt="implement approved scope",
            codex_prompt_specification_path=specification_path,
            codex_prompt_implementation_plan_path=implementation_plan_path,
            implementation_branch="developer",
            base_commit="abc123",
            working_directory=tmp_path,
            state_file=state_file,
            state_history_dir=tmp_path / "state_history",
        )
    )

    assert output.success is False
    assert output.current_state == "implementation_failed"
    assert output.technical_retry_required is False
    assert output.critical_change_required is False
    assert output.implementation_result is not None
    assert output.implementation_result.test_execution_status == "ERROR"

    current_state = state_file.read_text(encoding="utf-8")
    assert '"status": "implementation_failed"' in current_state


def test_safe_technical_error_is_retried_once_and_can_complete(
    tmp_path,
) -> None:
    specification_path = tmp_path / "specification.md"
    specification_path.write_text(
        "approved specification",
        encoding="utf-8",
    )

    implementation_plan_path = tmp_path / "implementation_plan.md"
    implementation_plan_path.write_text(
        "approved implementation plan",
        encoding="utf-8",
    )

    specification_record = build_approval_record_from_artifact(
        approval_id="spec-approval-001",
        artifact_type="specification",
        artifact_path=str(specification_path),
        decision="approved",
        approved_at="2026-09-09T10:00:00+09:00",
        comment="Specification approved.",
    )

    plan_record = build_approval_record_from_artifact(
        approval_id="plan-approval-001",
        artifact_type="implementation_plan",
        artifact_path=str(implementation_plan_path),
        decision="approved",
        approved_at="2026-09-09T10:01:00+09:00",
        comment="Implementation Plan approved.",
    )

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"status": "implementation_ready"}',
        encoding="utf-8",
    )

    initialize_clean_git_repository(tmp_path)

    class RetryThenSuccessAdapter:
        def __init__(self) -> None:
            self.call_count = 0

        def run(
            self,
            *,
            prompt: str,
            working_directory: Path,
        ) -> str:
            self.call_count += 1

            if self.call_count == 1:
                return """## Implementation Summary
TEST_REQUIRED: YES
Implementation could not complete because test execution failed.

## Changed Files
NONE

## Executed Commands
python -m pytest -q tests/test_example.py

## Test Execution Status
ERROR

## Test Result
NONE

## Test Execution Error
TECHNICAL_RETRY_SAFE: YES
TECHNICAL_RETRY_OPERATION: python -m pytest -q tests/test_example.py
Temporary test runner failure.

## Errors
Test execution error.

## Warnings
NONE

## Incomplete Items
NONE

## Human Approval Required
NONE
"""

            return """## Implementation Summary
TEST_REQUIRED: YES
Implementation completed after technical retry.

## Changed Files
application/example.py

## Executed Commands
python -m pytest -q tests/test_example.py

## Test Execution Status
COMPLETED

## Test Result
PASS

## Test Execution Error
TECHNICAL_RETRY_SAFE: NO
TECHNICAL_RETRY_OPERATION: NONE

## Errors
NONE

## Warnings
NONE

## Incomplete Items
NONE

## Human Approval Required
NONE
"""

    adapter = RetryThenSuccessAdapter()

    use_case = ExecuteImplementationUseCase(
        approval_repository=FakeApprovalRecordRepository(
            {
                "spec-approval-001": specification_record,
                "plan-approval-001": plan_record,
            }
        ),
        implementation_adapter=adapter,
    )

    output = use_case.execute(
        ExecuteImplementationInput(
            specification_path=specification_path,
            specification_approval_id="spec-approval-001",
            implementation_plan_path=implementation_plan_path,
            implementation_plan_approval_id="plan-approval-001",
            codex_prompt="implement approved scope",
            codex_prompt_specification_path=specification_path,
            codex_prompt_implementation_plan_path=implementation_plan_path,
            implementation_branch="developer",
            base_commit="abc123",
            working_directory=tmp_path,
            state_file=state_file,
            state_history_dir=tmp_path / "state_history",
        )
    )

    assert adapter.call_count == 2
    assert output.success is True
    assert output.current_state == "implementation_completed"
    assert output.technical_retry_required is False
    assert output.critical_change_required is False
    assert output.implementation_result is not None
    assert output.implementation_result.test_execution_status == "COMPLETED"
    assert output.implementation_result.test_result == "PASS"

    current_state = state_file.read_text(encoding="utf-8")
    assert '"status": "implementation_completed"' in current_state


def test_technical_retry_is_limited_to_one_attempt(
    tmp_path,
) -> None:
    specification_path = tmp_path / "specification.md"
    specification_path.write_text(
        "approved specification",
        encoding="utf-8",
    )

    implementation_plan_path = tmp_path / "implementation_plan.md"
    implementation_plan_path.write_text(
        "approved implementation plan",
        encoding="utf-8",
    )

    specification_record = build_approval_record_from_artifact(
        approval_id="spec-approval-001",
        artifact_type="specification",
        artifact_path=str(specification_path),
        decision="approved",
        approved_at="2026-09-09T10:00:00+09:00",
        comment="Specification approved.",
    )

    plan_record = build_approval_record_from_artifact(
        approval_id="plan-approval-001",
        artifact_type="implementation_plan",
        artifact_path=str(implementation_plan_path),
        decision="approved",
        approved_at="2026-09-09T10:01:00+09:00",
        comment="Implementation Plan approved.",
    )

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"status": "implementation_ready"}',
        encoding="utf-8",
    )

    initialize_clean_git_repository(tmp_path)

    class AlwaysTechnicalErrorAdapter:
        def __init__(self) -> None:
            self.call_count = 0

        def run(
            self,
            *,
            prompt: str,
            working_directory: Path,
        ) -> str:
            self.call_count += 1

            return """## Implementation Summary
TEST_REQUIRED: YES
Test execution failed because of a technical error.

## Changed Files
NONE

## Executed Commands
python -m pytest -q tests/test_example.py

## Test Execution Status
ERROR

## Test Result
NONE

## Test Execution Error
TECHNICAL_RETRY_SAFE: YES
TECHNICAL_RETRY_OPERATION: python -m pytest -q tests/test_example.py
Temporary test runner failure.

## Errors
Test execution error.

## Warnings
NONE

## Incomplete Items
NONE

## Human Approval Required
NONE
"""

    adapter = AlwaysTechnicalErrorAdapter()

    use_case = ExecuteImplementationUseCase(
        approval_repository=FakeApprovalRecordRepository(
            {
                "spec-approval-001": specification_record,
                "plan-approval-001": plan_record,
            }
        ),
        implementation_adapter=adapter,
    )

    output = use_case.execute(
        ExecuteImplementationInput(
            specification_path=specification_path,
            specification_approval_id="spec-approval-001",
            implementation_plan_path=implementation_plan_path,
            implementation_plan_approval_id="plan-approval-001",
            codex_prompt="implement approved scope",
            codex_prompt_specification_path=specification_path,
            codex_prompt_implementation_plan_path=implementation_plan_path,
            implementation_branch="developer",
            base_commit="abc123",
            working_directory=tmp_path,
            state_file=state_file,
            state_history_dir=tmp_path / "state_history",
        )
    )

    assert adapter.call_count == 2
    assert output.success is False
    assert output.current_state == "implementation_failed"
    assert output.technical_retry_required is False
    assert output.critical_change_required is False
    assert output.implementation_result is not None
    assert output.implementation_result.test_execution_status == "ERROR"

    current_state = state_file.read_text(encoding="utf-8")
    assert '"status": "implementation_failed"' in current_state


def test_human_approval_required_moves_to_critical_approval_pending(
    tmp_path,
) -> None:
    specification_path = tmp_path / "specification.md"
    specification_path.write_text(
        "approved specification",
        encoding="utf-8",
    )

    implementation_plan_path = tmp_path / "implementation_plan.md"
    implementation_plan_path.write_text(
        "approved implementation plan",
        encoding="utf-8",
    )

    specification_record = build_approval_record_from_artifact(
        approval_id="spec-approval-001",
        artifact_type="specification",
        artifact_path=str(specification_path),
        decision="approved",
        approved_at="2026-09-09T10:00:00+09:00",
        comment="Specification approved.",
    )

    plan_record = build_approval_record_from_artifact(
        approval_id="plan-approval-001",
        artifact_type="implementation_plan",
        artifact_path=str(implementation_plan_path),
        decision="approved",
        approved_at="2026-09-09T10:01:00+09:00",
        comment="Implementation Plan approved.",
    )

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"status": "implementation_ready"}',
        encoding="utf-8",
    )

    class CriticalChangeAdapter:
        def run(
            self,
            *,
            prompt: str,
            working_directory: Path,
        ) -> str:
            return """## Implementation Summary
TEST_REQUIRED: YES
Implementation requires a change outside the approved scope.

## Changed Files
NONE

## Executed Commands
NONE

## Test Execution Status
NOT_RUN

## Test Result
NONE

## Test Execution Error
TECHNICAL_RETRY_SAFE: NO
TECHNICAL_RETRY_OPERATION: NONE

## Errors
NONE

## Warnings
NONE

## Incomplete Items
Implementation stopped before the out-of-scope change.

## Human Approval Required
Database schema change is required outside the approved scope.
"""

    use_case = ExecuteImplementationUseCase(
        approval_repository=FakeApprovalRecordRepository(
            {
                "spec-approval-001": specification_record,
                "plan-approval-001": plan_record,
            }
        ),
        implementation_adapter=CriticalChangeAdapter(),
    )

    output = use_case.execute(
        ExecuteImplementationInput(
            specification_path=specification_path,
            specification_approval_id="spec-approval-001",
            implementation_plan_path=implementation_plan_path,
            implementation_plan_approval_id="plan-approval-001",
            codex_prompt="implement approved scope",
            codex_prompt_specification_path=specification_path,
            codex_prompt_implementation_plan_path=implementation_plan_path,
            implementation_branch="developer",
            base_commit="abc123",
            working_directory=tmp_path,
            state_file=state_file,
            state_history_dir=tmp_path / "state_history",
        )
    )

    assert output.success is False
    assert output.current_state == "critical_approval_pending"
    assert output.technical_retry_required is False
    assert output.critical_change_required is True
    assert output.implementation_result is not None
    assert (
        output.implementation_result.human_approval_required
        == "Database schema change is required outside the approved scope."
    )
    assert output.stop_reason == "Human Approval required."

    current_state = state_file.read_text(encoding="utf-8")
    assert '"status": "critical_approval_pending"' in current_state


def test_incomplete_items_prevent_implementation_completion(
    tmp_path,
) -> None:
    specification_path = tmp_path / "specification.md"
    specification_path.write_text(
        "approved specification",
        encoding="utf-8",
    )

    implementation_plan_path = tmp_path / "implementation_plan.md"
    implementation_plan_path.write_text(
        "approved implementation plan",
        encoding="utf-8",
    )

    specification_record = build_approval_record_from_artifact(
        approval_id="spec-approval-001",
        artifact_type="specification",
        artifact_path=str(specification_path),
        decision="approved",
        approved_at="2026-09-09T10:00:00+09:00",
        comment="Specification approved.",
    )

    plan_record = build_approval_record_from_artifact(
        approval_id="plan-approval-001",
        artifact_type="implementation_plan",
        artifact_path=str(implementation_plan_path),
        decision="approved",
        approved_at="2026-09-09T10:01:00+09:00",
        comment="Implementation Plan approved.",
    )

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"status": "implementation_ready"}',
        encoding="utf-8",
    )

    class IncompleteImplementationAdapter:
        def run(
            self,
            *,
            prompt: str,
            working_directory: Path,
        ) -> str:
            return """## Implementation Summary
TEST_REQUIRED: YES
Implementation stopped with incomplete work.

## Changed Files
application/example.py

## Executed Commands
python -m pytest -q tests/test_example.py

## Test Execution Status
COMPLETED

## Test Result
PASS

## Test Execution Error
TECHNICAL_RETRY_SAFE: NO
TECHNICAL_RETRY_OPERATION: NONE

## Errors
NONE

## Warnings
NONE

## Incomplete Items
One approved implementation item remains incomplete.

## Human Approval Required
NONE
"""

    use_case = ExecuteImplementationUseCase(
        approval_repository=FakeApprovalRecordRepository(
            {
                "spec-approval-001": specification_record,
                "plan-approval-001": plan_record,
            }
        ),
        implementation_adapter=IncompleteImplementationAdapter(),
    )

    output = use_case.execute(
        ExecuteImplementationInput(
            specification_path=specification_path,
            specification_approval_id="spec-approval-001",
            implementation_plan_path=implementation_plan_path,
            implementation_plan_approval_id="plan-approval-001",
            codex_prompt="implement approved scope",
            codex_prompt_specification_path=specification_path,
            codex_prompt_implementation_plan_path=implementation_plan_path,
            implementation_branch="developer",
            base_commit="abc123",
            working_directory=tmp_path,
            state_file=state_file,
            state_history_dir=tmp_path / "state_history",
        )
    )

    assert output.success is False
    assert output.current_state == "implementation_failed"
    assert output.technical_retry_required is False
    assert output.critical_change_required is False
    assert output.implementation_result is not None
    assert (
        output.implementation_result.incomplete_items
        == "One approved implementation item remains incomplete."
    )
    assert output.stop_reason == "Implementation incomplete."

    current_state = state_file.read_text(encoding="utf-8")
    assert '"status": "implementation_failed"' in current_state


def test_errors_prevent_implementation_completion(
    tmp_path,
) -> None:
    specification_path = tmp_path / "specification.md"
    specification_path.write_text(
        "approved specification",
        encoding="utf-8",
    )

    implementation_plan_path = tmp_path / "implementation_plan.md"
    implementation_plan_path.write_text(
        "approved implementation plan",
        encoding="utf-8",
    )

    specification_record = build_approval_record_from_artifact(
        approval_id="spec-approval-001",
        artifact_type="specification",
        artifact_path=str(specification_path),
        decision="approved",
        approved_at="2026-09-09T10:00:00+09:00",
        comment="Specification approved.",
    )

    plan_record = build_approval_record_from_artifact(
        approval_id="plan-approval-001",
        artifact_type="implementation_plan",
        artifact_path=str(implementation_plan_path),
        decision="approved",
        approved_at="2026-09-09T10:01:00+09:00",
        comment="Implementation Plan approved.",
    )

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"status": "implementation_ready"}',
        encoding="utf-8",
    )

    class ImplementationErrorAdapter:
        def run(
            self,
            *,
            prompt: str,
            working_directory: Path,
        ) -> str:
            return """## Implementation Summary
TEST_REQUIRED: YES
Implementation produced an error.

## Changed Files
application/example.py

## Executed Commands
python -m pytest -q tests/test_example.py

## Test Execution Status
COMPLETED

## Test Result
PASS

## Test Execution Error
TECHNICAL_RETRY_SAFE: NO
TECHNICAL_RETRY_OPERATION: NONE

## Errors
An implementation error remains unresolved.

## Warnings
NONE

## Incomplete Items
NONE

## Human Approval Required
NONE
"""

    use_case = ExecuteImplementationUseCase(
        approval_repository=FakeApprovalRecordRepository(
            {
                "spec-approval-001": specification_record,
                "plan-approval-001": plan_record,
            }
        ),
        implementation_adapter=ImplementationErrorAdapter(),
    )

    output = use_case.execute(
        ExecuteImplementationInput(
            specification_path=specification_path,
            specification_approval_id="spec-approval-001",
            implementation_plan_path=implementation_plan_path,
            implementation_plan_approval_id="plan-approval-001",
            codex_prompt="implement approved scope",
            codex_prompt_specification_path=specification_path,
            codex_prompt_implementation_plan_path=implementation_plan_path,
            implementation_branch="developer",
            base_commit="abc123",
            working_directory=tmp_path,
            state_file=state_file,
            state_history_dir=tmp_path / "state_history",
        )
    )

    assert output.success is False
    assert output.current_state == "implementation_failed"
    assert output.technical_retry_required is False
    assert output.critical_change_required is False
    assert output.implementation_result is not None
    assert (
        output.implementation_result.errors
        == "An implementation error remains unresolved."
    )
    assert output.stop_reason == "Implementation error reported."

    current_state = state_file.read_text(encoding="utf-8")
    assert '"status": "implementation_failed"' in current_state


def test_required_tests_not_run_prevent_implementation_completion(
    tmp_path,
) -> None:
    specification_path = tmp_path / "specification.md"
    specification_path.write_text(
        "approved specification",
        encoding="utf-8",
    )

    implementation_plan_path = tmp_path / "implementation_plan.md"
    implementation_plan_path.write_text(
        "approved implementation plan",
        encoding="utf-8",
    )

    specification_record = build_approval_record_from_artifact(
        approval_id="spec-approval-001",
        artifact_type="specification",
        artifact_path=str(specification_path),
        decision="approved",
        approved_at="2026-09-09T10:00:00+09:00",
        comment="Specification approved.",
    )

    plan_record = build_approval_record_from_artifact(
        approval_id="plan-approval-001",
        artifact_type="implementation_plan",
        artifact_path=str(implementation_plan_path),
        decision="approved",
        approved_at="2026-09-09T10:01:00+09:00",
        comment="Implementation Plan approved.",
    )

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"status": "implementation_ready"}',
        encoding="utf-8",
    )

    class RequiredTestsNotRunAdapter:
        def run(
            self,
            *,
            prompt: str,
            working_directory: Path,
        ) -> str:
            return """## Implementation Summary
TEST_REQUIRED: YES
Implementation was performed but required tests were not run.

## Changed Files
application/example.py

## Executed Commands
NONE

## Test Execution Status
NOT_RUN

## Test Result
NONE

## Test Execution Error
TECHNICAL_RETRY_SAFE: NO
TECHNICAL_RETRY_OPERATION: NONE

## Errors
NONE

## Warnings
NONE

## Incomplete Items
NONE

## Human Approval Required
NONE
"""

    use_case = ExecuteImplementationUseCase(
        approval_repository=FakeApprovalRecordRepository(
            {
                "spec-approval-001": specification_record,
                "plan-approval-001": plan_record,
            }
        ),
        implementation_adapter=RequiredTestsNotRunAdapter(),
    )

    output = use_case.execute(
        ExecuteImplementationInput(
            specification_path=specification_path,
            specification_approval_id="spec-approval-001",
            implementation_plan_path=implementation_plan_path,
            implementation_plan_approval_id="plan-approval-001",
            codex_prompt="implement approved scope",
            codex_prompt_specification_path=specification_path,
            codex_prompt_implementation_plan_path=implementation_plan_path,
            implementation_branch="developer",
            base_commit="abc123",
            working_directory=tmp_path,
            state_file=state_file,
            state_history_dir=tmp_path / "state_history",
        )
    )

    assert output.success is False
    assert output.current_state == "implementation_failed"
    assert output.technical_retry_required is False
    assert output.critical_change_required is False
    assert output.implementation_result is not None
    assert output.implementation_result.test_required is True
    assert (
        output.implementation_result.test_execution_status
        == "NOT_RUN"
    )
    assert output.stop_reason == "Required tests were not run."

    current_state = state_file.read_text(encoding="utf-8")
    assert '"status": "implementation_failed"' in current_state


def test_tests_not_required_and_not_run_can_complete(
    tmp_path,
) -> None:
    specification_path = tmp_path / "specification.md"
    specification_path.write_text(
        "approved specification",
        encoding="utf-8",
    )

    implementation_plan_path = tmp_path / "implementation_plan.md"
    implementation_plan_path.write_text(
        "approved implementation plan",
        encoding="utf-8",
    )

    specification_record = build_approval_record_from_artifact(
        approval_id="spec-approval-001",
        artifact_type="specification",
        artifact_path=str(specification_path),
        decision="approved",
        approved_at="2026-09-09T10:00:00+09:00",
        comment="Specification approved.",
    )

    plan_record = build_approval_record_from_artifact(
        approval_id="plan-approval-001",
        artifact_type="implementation_plan",
        artifact_path=str(implementation_plan_path),
        decision="approved",
        approved_at="2026-09-09T10:01:00+09:00",
        comment="Implementation Plan approved.",
    )

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"status": "implementation_ready"}',
        encoding="utf-8",
    )

    class NoTestsRequiredAdapter:
        def run(
            self,
            *,
            prompt: str,
            working_directory: Path,
        ) -> str:
            return """## Implementation Summary
TEST_REQUIRED: NO
Documentation-only implementation completed.

## Changed Files
docs/example.md

## Executed Commands
NONE

## Test Execution Status
NOT_RUN

## Test Result
NONE

## Test Execution Error
TECHNICAL_RETRY_SAFE: NO
TECHNICAL_RETRY_OPERATION: NONE

## Errors
NONE

## Warnings
NONE

## Incomplete Items
NONE

## Human Approval Required
NONE
"""

    use_case = ExecuteImplementationUseCase(
        approval_repository=FakeApprovalRecordRepository(
            {
                "spec-approval-001": specification_record,
                "plan-approval-001": plan_record,
            }
        ),
        implementation_adapter=NoTestsRequiredAdapter(),
    )

    output = use_case.execute(
        ExecuteImplementationInput(
            specification_path=specification_path,
            specification_approval_id="spec-approval-001",
            implementation_plan_path=implementation_plan_path,
            implementation_plan_approval_id="plan-approval-001",
            codex_prompt="implement approved scope",
            codex_prompt_specification_path=specification_path,
            codex_prompt_implementation_plan_path=implementation_plan_path,
            implementation_branch="developer",
            base_commit="abc123",
            working_directory=tmp_path,
            state_file=state_file,
            state_history_dir=tmp_path / "state_history",
        )
    )

    assert output.success is True
    assert output.current_state == "implementation_completed"
    assert output.technical_retry_required is False
    assert output.critical_change_required is False
    assert output.implementation_result is not None
    assert output.implementation_result.test_required is False
    assert (
        output.implementation_result.test_execution_status
        == "NOT_RUN"
    )

    current_state = state_file.read_text(encoding="utf-8")
    assert '"status": "implementation_completed"' in current_state


def test_warnings_alone_do_not_prevent_completion(
    tmp_path,
) -> None:
    specification_path = tmp_path / "specification.md"
    specification_path.write_text(
        "approved specification",
        encoding="utf-8",
    )

    implementation_plan_path = tmp_path / "implementation_plan.md"
    implementation_plan_path.write_text(
        "approved implementation plan",
        encoding="utf-8",
    )

    specification_record = build_approval_record_from_artifact(
        approval_id="spec-approval-001",
        artifact_type="specification",
        artifact_path=str(specification_path),
        decision="approved",
        approved_at="2026-09-09T10:00:00+09:00",
        comment="Specification approved.",
    )

    plan_record = build_approval_record_from_artifact(
        approval_id="plan-approval-001",
        artifact_type="implementation_plan",
        artifact_path=str(implementation_plan_path),
        decision="approved",
        approved_at="2026-09-09T10:01:00+09:00",
        comment="Implementation Plan approved.",
    )

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"status": "implementation_ready"}',
        encoding="utf-8",
    )

    class WarningOnlyAdapter:
        def run(
            self,
            *,
            prompt: str,
            working_directory: Path,
        ) -> str:
            return """## Implementation Summary
TEST_REQUIRED: YES
Implementation completed with a warning.

## Changed Files
application/example.py

## Executed Commands
python -m pytest -q tests/test_example.py

## Test Execution Status
COMPLETED

## Test Result
PASS

## Test Execution Error
TECHNICAL_RETRY_SAFE: NO
TECHNICAL_RETRY_OPERATION: NONE

## Errors
NONE

## Warnings
A non-blocking warning was reported.

## Incomplete Items
NONE

## Human Approval Required
NONE
"""

    use_case = ExecuteImplementationUseCase(
        approval_repository=FakeApprovalRecordRepository(
            {
                "spec-approval-001": specification_record,
                "plan-approval-001": plan_record,
            }
        ),
        implementation_adapter=WarningOnlyAdapter(),
    )

    output = use_case.execute(
        ExecuteImplementationInput(
            specification_path=specification_path,
            specification_approval_id="spec-approval-001",
            implementation_plan_path=implementation_plan_path,
            implementation_plan_approval_id="plan-approval-001",
            codex_prompt="implement approved scope",
            codex_prompt_specification_path=specification_path,
            codex_prompt_implementation_plan_path=implementation_plan_path,
            implementation_branch="developer",
            base_commit="abc123",
            working_directory=tmp_path,
            state_file=state_file,
            state_history_dir=tmp_path / "state_history",
        )
    )

    assert output.success is True
    assert output.current_state == "implementation_completed"
    assert output.technical_retry_required is False
    assert output.critical_change_required is False
    assert output.implementation_result is not None
    assert (
        output.implementation_result.warnings
        == "A non-blocking warning was reported."
    )

    current_state = state_file.read_text(encoding="utf-8")
    assert '"status": "implementation_completed"' in current_state


def test_runner_exception_fails_without_automatic_retry(
    tmp_path,
) -> None:
    specification_path = tmp_path / "specification.md"
    specification_path.write_text(
        "approved specification",
        encoding="utf-8",
    )

    implementation_plan_path = tmp_path / "implementation_plan.md"
    implementation_plan_path.write_text(
        "approved implementation plan",
        encoding="utf-8",
    )

    specification_record = build_approval_record_from_artifact(
        approval_id="spec-approval-001",
        artifact_type="specification",
        artifact_path=str(specification_path),
        decision="approved",
        approved_at="2026-09-09T10:00:00+09:00",
        comment="Specification approved.",
    )

    plan_record = build_approval_record_from_artifact(
        approval_id="plan-approval-001",
        artifact_type="implementation_plan",
        artifact_path=str(implementation_plan_path),
        decision="approved",
        approved_at="2026-09-09T10:01:00+09:00",
        comment="Implementation Plan approved.",
    )

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"status": "implementation_ready"}',
        encoding="utf-8",
    )

    class FailingRunnerAdapter:
        def __init__(self) -> None:
            self.call_count = 0

        def run(
            self,
            *,
            prompt: str,
            working_directory: Path,
        ) -> str:
            self.call_count += 1
            raise RuntimeError("Codex runner unavailable")

    adapter = FailingRunnerAdapter()

    use_case = ExecuteImplementationUseCase(
        approval_repository=FakeApprovalRecordRepository(
            {
                "spec-approval-001": specification_record,
                "plan-approval-001": plan_record,
            }
        ),
        implementation_adapter=adapter,
    )

    output = use_case.execute(
        ExecuteImplementationInput(
            specification_path=specification_path,
            specification_approval_id="spec-approval-001",
            implementation_plan_path=implementation_plan_path,
            implementation_plan_approval_id="plan-approval-001",
            codex_prompt="implement approved scope",
            codex_prompt_specification_path=specification_path,
            codex_prompt_implementation_plan_path=implementation_plan_path,
            implementation_branch="developer",
            base_commit="abc123",
            working_directory=tmp_path,
            state_file=state_file,
            state_history_dir=tmp_path / "state_history",
        )
    )

    assert adapter.call_count == 1
    assert output.success is False
    assert output.implementation_result is None
    assert output.current_state == "implementation_failed"
    assert output.technical_retry_required is False
    assert output.critical_change_required is False
    assert output.stop_reason == "Implementation runner error."
    assert output.error_message == "Codex runner unavailable"

    current_state = state_file.read_text(encoding="utf-8")
    assert '"status": "implementation_failed"' in current_state


def test_parser_error_fails_without_automatic_retry(
    tmp_path,
) -> None:
    specification_path = tmp_path / "specification.md"
    specification_path.write_text(
        "approved specification",
        encoding="utf-8",
    )

    implementation_plan_path = tmp_path / "implementation_plan.md"
    implementation_plan_path.write_text(
        "approved implementation plan",
        encoding="utf-8",
    )

    specification_record = build_approval_record_from_artifact(
        approval_id="spec-approval-001",
        artifact_type="specification",
        artifact_path=str(specification_path),
        decision="approved",
        approved_at="2026-09-09T10:00:00+09:00",
        comment="Specification approved.",
    )

    plan_record = build_approval_record_from_artifact(
        approval_id="plan-approval-001",
        artifact_type="implementation_plan",
        artifact_path=str(implementation_plan_path),
        decision="approved",
        approved_at="2026-09-09T10:01:00+09:00",
        comment="Implementation Plan approved.",
    )

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"status": "implementation_ready"}',
        encoding="utf-8",
    )

    class InvalidOutputAdapter:
        def __init__(self) -> None:
            self.call_count = 0

        def run(
            self,
            *,
            prompt: str,
            working_directory: Path,
        ) -> str:
            self.call_count += 1
            return """## Implementation Summary
TEST_REQUIRED: YES
Codex returned an incomplete structured result.

## Changed Files
application/example.py
"""

    adapter = InvalidOutputAdapter()

    use_case = ExecuteImplementationUseCase(
        approval_repository=FakeApprovalRecordRepository(
            {
                "spec-approval-001": specification_record,
                "plan-approval-001": plan_record,
            }
        ),
        implementation_adapter=adapter,
    )

    output = use_case.execute(
        ExecuteImplementationInput(
            specification_path=specification_path,
            specification_approval_id="spec-approval-001",
            implementation_plan_path=implementation_plan_path,
            implementation_plan_approval_id="plan-approval-001",
            codex_prompt="implement approved scope",
            codex_prompt_specification_path=specification_path,
            codex_prompt_implementation_plan_path=implementation_plan_path,
            implementation_branch="developer",
            base_commit="abc123",
            working_directory=tmp_path,
            state_file=state_file,
            state_history_dir=tmp_path / "state_history",
        )
    )

    assert adapter.call_count == 1
    assert output.success is False
    assert output.implementation_result is None
    assert output.current_state == "implementation_failed"
    assert output.technical_retry_required is False
    assert output.critical_change_required is False
    assert output.stop_reason == "Implementation result parse error."
    assert output.error_message is not None

    current_state = state_file.read_text(encoding="utf-8")
    assert '"status": "implementation_failed"' in current_state


def test_runner_exception_during_technical_retry_fails_safely(
    tmp_path,
) -> None:
    specification_path = tmp_path / "specification.md"
    specification_path.write_text(
        "approved specification",
        encoding="utf-8",
    )

    implementation_plan_path = tmp_path / "implementation_plan.md"
    implementation_plan_path.write_text(
        "approved implementation plan",
        encoding="utf-8",
    )

    specification_record = build_approval_record_from_artifact(
        approval_id="spec-approval-001",
        artifact_type="specification",
        artifact_path=str(specification_path),
        decision="approved",
        approved_at="2026-09-09T10:00:00+09:00",
        comment="Specification approved.",
    )

    plan_record = build_approval_record_from_artifact(
        approval_id="plan-approval-001",
        artifact_type="implementation_plan",
        artifact_path=str(implementation_plan_path),
        decision="approved",
        approved_at="2026-09-09T10:01:00+09:00",
        comment="Implementation Plan approved.",
    )

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"status": "implementation_ready"}',
        encoding="utf-8",
    )

    initialize_clean_git_repository(tmp_path)

    class RetryRunnerFailureAdapter:
        def __init__(self) -> None:
            self.call_count = 0

        def run(
            self,
            *,
            prompt: str,
            working_directory: Path,
        ) -> str:
            self.call_count += 1

            if self.call_count == 1:
                return """## Implementation Summary
TEST_REQUIRED: YES
Technical test execution error occurred.

## Changed Files
NONE

## Executed Commands
python -m pytest -q tests/test_example.py

## Test Execution Status
ERROR

## Test Result
NONE

## Test Execution Error
TECHNICAL_RETRY_SAFE: YES
TECHNICAL_RETRY_OPERATION: python -m pytest -q tests/test_example.py

## Errors
Test execution error.

## Warnings
NONE

## Incomplete Items
NONE

## Human Approval Required
NONE
"""

            raise RuntimeError("Codex runner failed during retry")

    adapter = RetryRunnerFailureAdapter()

    use_case = ExecuteImplementationUseCase(
        approval_repository=FakeApprovalRecordRepository(
            {
                "spec-approval-001": specification_record,
                "plan-approval-001": plan_record,
            }
        ),
        implementation_adapter=adapter,
    )

    output = use_case.execute(
        ExecuteImplementationInput(
            specification_path=specification_path,
            specification_approval_id="spec-approval-001",
            implementation_plan_path=implementation_plan_path,
            implementation_plan_approval_id="plan-approval-001",
            codex_prompt="implement approved scope",
            codex_prompt_specification_path=specification_path,
            codex_prompt_implementation_plan_path=implementation_plan_path,
            implementation_branch="developer",
            base_commit="abc123",
            working_directory=tmp_path,
            state_file=state_file,
            state_history_dir=tmp_path / "state_history",
        )
    )

    assert adapter.call_count == 2
    assert output.success is False
    assert output.current_state == "implementation_failed"
    assert output.technical_retry_required is False
    assert output.critical_change_required is False
    assert output.stop_reason == "Implementation runner error."
    assert output.error_message == "Codex runner failed during retry"

    current_state = state_file.read_text(encoding="utf-8")
    assert '"status": "implementation_failed"' in current_state


def test_parser_error_during_technical_retry_fails_safely(
    tmp_path,
) -> None:
    specification_path = tmp_path / "specification.md"
    specification_path.write_text(
        "approved specification",
        encoding="utf-8",
    )

    implementation_plan_path = tmp_path / "implementation_plan.md"
    implementation_plan_path.write_text(
        "approved implementation plan",
        encoding="utf-8",
    )

    specification_record = build_approval_record_from_artifact(
        approval_id="spec-approval-001",
        artifact_type="specification",
        artifact_path=str(specification_path),
        decision="approved",
        approved_at="2026-09-09T10:00:00+09:00",
        comment="Specification approved.",
    )

    plan_record = build_approval_record_from_artifact(
        approval_id="plan-approval-001",
        artifact_type="implementation_plan",
        artifact_path=str(implementation_plan_path),
        decision="approved",
        approved_at="2026-09-09T10:01:00+09:00",
        comment="Implementation Plan approved.",
    )

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"status": "implementation_ready"}',
        encoding="utf-8",
    )

    initialize_clean_git_repository(tmp_path)

    class RetryInvalidOutputAdapter:
        def __init__(self) -> None:
            self.call_count = 0

        def run(
            self,
            *,
            prompt: str,
            working_directory: Path,
        ) -> str:
            self.call_count += 1

            if self.call_count == 1:
                return """## Implementation Summary
TEST_REQUIRED: YES
Technical test execution error occurred.

## Changed Files
NONE

## Executed Commands
python -m pytest -q tests/test_example.py

## Test Execution Status
ERROR

## Test Result
NONE

## Test Execution Error
TECHNICAL_RETRY_SAFE: YES
TECHNICAL_RETRY_OPERATION: python -m pytest -q tests/test_example.py

## Errors
Test execution error.

## Warnings
NONE

## Incomplete Items
NONE

## Human Approval Required
NONE
"""

            return """## Implementation Summary
TEST_REQUIRED: YES
Retry returned an incomplete structured result.

## Changed Files
NONE
"""

    adapter = RetryInvalidOutputAdapter()

    use_case = ExecuteImplementationUseCase(
        approval_repository=FakeApprovalRecordRepository(
            {
                "spec-approval-001": specification_record,
                "plan-approval-001": plan_record,
            }
        ),
        implementation_adapter=adapter,
    )

    output = use_case.execute(
        ExecuteImplementationInput(
            specification_path=specification_path,
            specification_approval_id="spec-approval-001",
            implementation_plan_path=implementation_plan_path,
            implementation_plan_approval_id="plan-approval-001",
            codex_prompt="implement approved scope",
            codex_prompt_specification_path=specification_path,
            codex_prompt_implementation_plan_path=implementation_plan_path,
            implementation_branch="developer",
            base_commit="abc123",
            working_directory=tmp_path,
            state_file=state_file,
            state_history_dir=tmp_path / "state_history",
        )
    )

    assert adapter.call_count == 2
    assert output.success is False
    assert output.current_state == "implementation_failed"
    assert output.technical_retry_required is False
    assert output.critical_change_required is False
    assert output.stop_reason == "Implementation result parse error."
    assert output.error_message is not None

    current_state = state_file.read_text(encoding="utf-8")
    assert '"status": "implementation_failed"' in current_state


def test_human_approval_required_after_technical_retry_stops_as_critical(
    tmp_path,
) -> None:
    specification_path = tmp_path / "specification.md"
    specification_path.write_text(
        "approved specification",
        encoding="utf-8",
    )

    implementation_plan_path = tmp_path / "implementation_plan.md"
    implementation_plan_path.write_text(
        "approved implementation plan",
        encoding="utf-8",
    )

    specification_record = build_approval_record_from_artifact(
        approval_id="spec-approval-001",
        artifact_type="specification",
        artifact_path=str(specification_path),
        decision="approved",
        approved_at="2026-09-09T10:00:00+09:00",
        comment="Specification approved.",
    )

    plan_record = build_approval_record_from_artifact(
        approval_id="plan-approval-001",
        artifact_type="implementation_plan",
        artifact_path=str(implementation_plan_path),
        decision="approved",
        approved_at="2026-09-09T10:01:00+09:00",
        comment="Implementation Plan approved.",
    )

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"status": "implementation_ready"}',
        encoding="utf-8",
    )

    initialize_clean_git_repository(tmp_path)

    class RetryRequiresHumanApprovalAdapter:
        def __init__(self) -> None:
            self.call_count = 0

        def run(
            self,
            *,
            prompt: str,
            working_directory: Path,
        ) -> str:
            self.call_count += 1

            if self.call_count == 1:
                return """## Implementation Summary
TEST_REQUIRED: YES
Technical test execution error occurred.

## Changed Files
NONE

## Executed Commands
python -m pytest -q tests/test_example.py

## Test Execution Status
ERROR

## Test Result
NONE

## Test Execution Error
TECHNICAL_RETRY_SAFE: YES
TECHNICAL_RETRY_OPERATION: python -m pytest -q tests/test_example.py

## Errors
Test execution error.

## Warnings
NONE

## Incomplete Items
NONE

## Human Approval Required
NONE
"""

            return """## Implementation Summary
TEST_REQUIRED: YES
Retry discovered a change outside the approved scope.

## Changed Files
NONE

## Executed Commands
python -m pytest -q tests/test_example.py

## Test Execution Status
COMPLETED

## Test Result
PASS

## Test Execution Error
TECHNICAL_RETRY_SAFE: NO
TECHNICAL_RETRY_OPERATION: NONE

## Errors
NONE

## Warnings
NONE

## Incomplete Items
NONE

## Human Approval Required
Change outside approved implementation scope.
"""

    adapter = RetryRequiresHumanApprovalAdapter()

    use_case = ExecuteImplementationUseCase(
        approval_repository=FakeApprovalRecordRepository(
            {
                "spec-approval-001": specification_record,
                "plan-approval-001": plan_record,
            }
        ),
        implementation_adapter=adapter,
    )

    output = use_case.execute(
        ExecuteImplementationInput(
            specification_path=specification_path,
            specification_approval_id="spec-approval-001",
            implementation_plan_path=implementation_plan_path,
            implementation_plan_approval_id="plan-approval-001",
            codex_prompt="implement approved scope",
            codex_prompt_specification_path=specification_path,
            codex_prompt_implementation_plan_path=implementation_plan_path,
            implementation_branch="developer",
            base_commit="abc123",
            working_directory=tmp_path,
            state_file=state_file,
            state_history_dir=tmp_path / "state_history",
        )
    )

    assert adapter.call_count == 2
    assert output.success is False
    assert output.current_state == "critical_approval_pending"
    assert output.technical_retry_required is False
    assert output.critical_change_required is True
    assert output.stop_reason == "Human Approval required."

    current_state = state_file.read_text(encoding="utf-8")
    assert '"status": "critical_approval_pending"' in current_state


def test_incomplete_items_after_technical_retry_fails(
    tmp_path,
) -> None:
    specification_path = tmp_path / "specification.md"
    specification_path.write_text(
        "approved specification",
        encoding="utf-8",
    )

    implementation_plan_path = tmp_path / "implementation_plan.md"
    implementation_plan_path.write_text(
        "approved implementation plan",
        encoding="utf-8",
    )

    specification_record = build_approval_record_from_artifact(
        approval_id="spec-approval-001",
        artifact_type="specification",
        artifact_path=str(specification_path),
        decision="approved",
        approved_at="2026-09-09T10:00:00+09:00",
        comment="Specification approved.",
    )

    plan_record = build_approval_record_from_artifact(
        approval_id="plan-approval-001",
        artifact_type="implementation_plan",
        artifact_path=str(implementation_plan_path),
        decision="approved",
        approved_at="2026-09-09T10:01:00+09:00",
        comment="Implementation Plan approved.",
    )

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"status": "implementation_ready"}',
        encoding="utf-8",
    )

    initialize_clean_git_repository(tmp_path)

    class RetryIncompleteAdapter:
        def __init__(self) -> None:
            self.call_count = 0

        def run(
            self,
            *,
            prompt: str,
            working_directory: Path,
        ) -> str:
            self.call_count += 1

            if self.call_count == 1:
                return """## Implementation Summary
TEST_REQUIRED: YES
Technical test execution error occurred.

## Changed Files
NONE

## Executed Commands
python -m pytest -q tests/test_example.py

## Test Execution Status
ERROR

## Test Result
NONE

## Test Execution Error
TECHNICAL_RETRY_SAFE: YES
TECHNICAL_RETRY_OPERATION: python -m pytest -q tests/test_example.py

## Errors
Test execution error.

## Warnings
NONE

## Incomplete Items
NONE

## Human Approval Required
NONE
"""

            return """## Implementation Summary
TEST_REQUIRED: YES
Retry completed but implementation remains incomplete.

## Changed Files
NONE

## Executed Commands
python -m pytest -q tests/test_example.py

## Test Execution Status
COMPLETED

## Test Result
PASS

## Test Execution Error
TECHNICAL_RETRY_SAFE: NO
TECHNICAL_RETRY_OPERATION: NONE

## Errors
NONE

## Warnings
NONE

## Incomplete Items
Required implementation step remains incomplete.

## Human Approval Required
NONE
"""

    adapter = RetryIncompleteAdapter()

    use_case = ExecuteImplementationUseCase(
        approval_repository=FakeApprovalRecordRepository(
            {
                "spec-approval-001": specification_record,
                "plan-approval-001": plan_record,
            }
        ),
        implementation_adapter=adapter,
    )

    output = use_case.execute(
        ExecuteImplementationInput(
            specification_path=specification_path,
            specification_approval_id="spec-approval-001",
            implementation_plan_path=implementation_plan_path,
            implementation_plan_approval_id="plan-approval-001",
            codex_prompt="implement approved scope",
            codex_prompt_specification_path=specification_path,
            codex_prompt_implementation_plan_path=implementation_plan_path,
            implementation_branch="developer",
            base_commit="abc123",
            working_directory=tmp_path,
            state_file=state_file,
            state_history_dir=tmp_path / "state_history",
        )
    )

    assert adapter.call_count == 2
    assert output.success is False
    assert output.current_state == "implementation_failed"
    assert output.technical_retry_required is False
    assert output.critical_change_required is False
    assert output.stop_reason == "Implementation incomplete."

    current_state = state_file.read_text(encoding="utf-8")
    assert '"status": "implementation_failed"' in current_state


def test_technical_retry_is_not_allowed_when_git_working_tree_has_changes(
    tmp_path,
) -> None:
    import subprocess

    specification_path = tmp_path / "specification.md"
    specification_path.write_text(
        "approved specification",
        encoding="utf-8",
    )

    implementation_plan_path = tmp_path / "implementation_plan.md"
    implementation_plan_path.write_text(
        "approved implementation plan",
        encoding="utf-8",
    )

    specification_record = build_approval_record_from_artifact(
        approval_id="spec-approval-001",
        artifact_type="specification",
        artifact_path=str(specification_path),
        decision="approved",
        approved_at="2026-09-09T10:00:00+09:00",
        comment="Specification approved.",
    )

    plan_record = build_approval_record_from_artifact(
        approval_id="plan-approval-001",
        artifact_type="implementation_plan",
        artifact_path=str(implementation_plan_path),
        decision="approved",
        approved_at="2026-09-09T10:01:00+09:00",
        comment="Implementation Plan approved.",
    )

    subprocess.run(
        ["git", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "specflow@example.com"],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "SpecFlow Test"],
        cwd=tmp_path,
        check=True,
    )

    tracked_file = tmp_path / "tracked.txt"
    tracked_file.write_text("initial\n", encoding="utf-8")

    subprocess.run(
        ["git", "add", "tracked.txt"],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    tracked_file.write_text(
        "initial\nmodified\n",
        encoding="utf-8",
    )

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"status": "implementation_ready"}',
        encoding="utf-8",
    )

    class TechnicalRetryCandidateAdapter:
        def __init__(self) -> None:
            self.call_count = 0

        def run(
            self,
            *,
            prompt: str,
            working_directory: Path,
        ) -> str:
            self.call_count += 1

            return """## Implementation Summary
TEST_REQUIRED: YES
Test execution failed because of a technical error.

## Changed Files
NONE

## Executed Commands
python -m pytest -q tests/test_example.py

## Test Execution Status
ERROR

## Test Result
NONE

## Test Execution Error
TECHNICAL_RETRY_SAFE: YES
TECHNICAL_RETRY_OPERATION: python -m pytest -q tests/test_example.py
Temporary test runner failure.

## Errors
Test execution error.

## Warnings
NONE

## Incomplete Items
NONE

## Human Approval Required
NONE
"""

    adapter = TechnicalRetryCandidateAdapter()

    use_case = ExecuteImplementationUseCase(
        approval_repository=FakeApprovalRecordRepository(
            {
                "spec-approval-001": specification_record,
                "plan-approval-001": plan_record,
            }
        ),
        implementation_adapter=adapter,
    )

    output = use_case.execute(
        ExecuteImplementationInput(
            specification_path=specification_path,
            specification_approval_id="spec-approval-001",
            implementation_plan_path=implementation_plan_path,
            implementation_plan_approval_id="plan-approval-001",
            codex_prompt="implement approved scope",
            codex_prompt_specification_path=specification_path,
            codex_prompt_implementation_plan_path=implementation_plan_path,
            implementation_branch="developer",
            base_commit="abc123",
            working_directory=tmp_path,
            state_file=state_file,
            state_history_dir=tmp_path / "state_history",
        )
    )

    assert adapter.call_count == 1
    assert output.success is False
    assert output.current_state == "implementation_failed"
    assert output.technical_retry_required is False
    assert output.critical_change_required is False
    assert output.stop_reason == "Test execution error."


def test_technical_retry_is_not_allowed_when_git_state_cannot_be_verified(
    tmp_path,
) -> None:
    specification_path = tmp_path / "specification.md"
    specification_path.write_text(
        "approved specification",
        encoding="utf-8",
    )

    implementation_plan_path = tmp_path / "implementation_plan.md"
    implementation_plan_path.write_text(
        "approved implementation plan",
        encoding="utf-8",
    )

    specification_record = build_approval_record_from_artifact(
        approval_id="spec-approval-001",
        artifact_type="specification",
        artifact_path=str(specification_path),
        decision="approved",
        approved_at="2026-09-09T10:00:00+09:00",
        comment="Specification approved.",
    )

    plan_record = build_approval_record_from_artifact(
        approval_id="plan-approval-001",
        artifact_type="implementation_plan",
        artifact_path=str(implementation_plan_path),
        decision="approved",
        approved_at="2026-09-09T10:01:00+09:00",
        comment="Implementation Plan approved.",
    )

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"status": "implementation_ready"}',
        encoding="utf-8",
    )

    class TechnicalRetryCandidateAdapter:
        def __init__(self) -> None:
            self.call_count = 0

        def run(
            self,
            *,
            prompt: str,
            working_directory: Path,
        ) -> str:
            self.call_count += 1

            return """## Implementation Summary
TEST_REQUIRED: YES
Test execution failed because of a technical error.

## Changed Files
NONE

## Executed Commands
python -m pytest -q tests/test_example.py

## Test Execution Status
ERROR

## Test Result
NONE

## Test Execution Error
TECHNICAL_RETRY_SAFE: YES
TECHNICAL_RETRY_OPERATION: python -m pytest -q tests/test_example.py
Temporary test runner failure.

## Errors
Test execution error.

## Warnings
NONE

## Incomplete Items
NONE

## Human Approval Required
NONE
"""

    adapter = TechnicalRetryCandidateAdapter()

    use_case = ExecuteImplementationUseCase(
        approval_repository=FakeApprovalRecordRepository(
            {
                "spec-approval-001": specification_record,
                "plan-approval-001": plan_record,
            }
        ),
        implementation_adapter=adapter,
    )

    output = use_case.execute(
        ExecuteImplementationInput(
            specification_path=specification_path,
            specification_approval_id="spec-approval-001",
            implementation_plan_path=implementation_plan_path,
            implementation_plan_approval_id="plan-approval-001",
            codex_prompt="implement approved scope",
            codex_prompt_specification_path=specification_path,
            codex_prompt_implementation_plan_path=implementation_plan_path,
            implementation_branch="developer",
            base_commit="abc123",
            working_directory=tmp_path,
            state_file=state_file,
            state_history_dir=tmp_path / "state_history",
        )
    )

    assert adapter.call_count == 1
    assert output.success is False
    assert output.current_state == "implementation_failed"
    assert output.technical_retry_required is False
    assert output.critical_change_required is False
    assert output.stop_reason == "Test execution error."


def test_implementation_does_not_start_from_invalid_current_state(
    tmp_path,
) -> None:
    specification_path = tmp_path / "specification.md"
    specification_path.write_text(
        "approved specification",
        encoding="utf-8",
    )

    implementation_plan_path = tmp_path / "implementation_plan.md"
    implementation_plan_path.write_text(
        "approved implementation plan",
        encoding="utf-8",
    )

    specification_record = build_approval_record_from_artifact(
        approval_id="spec-approval-001",
        artifact_type="specification",
        artifact_path=str(specification_path),
        decision="approved",
        approved_at="2026-09-09T10:00:00+09:00",
        comment="Specification approved.",
    )

    plan_record = build_approval_record_from_artifact(
        approval_id="plan-approval-001",
        artifact_type="implementation_plan",
        artifact_path=str(implementation_plan_path),
        decision="approved",
        approved_at="2026-09-09T10:01:00+09:00",
        comment="Implementation Plan approved.",
    )

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"status": "plan_approved"}',
        encoding="utf-8",
    )

    class ShouldNotRunAdapter:
        def __init__(self) -> None:
            self.call_count = 0

        def run(
            self,
            *,
            prompt: str,
            working_directory: Path,
        ) -> str:
            self.call_count += 1
            raise AssertionError("Runner must not be called.")

    adapter = ShouldNotRunAdapter()

    use_case = ExecuteImplementationUseCase(
        approval_repository=FakeApprovalRecordRepository(
            {
                "spec-approval-001": specification_record,
                "plan-approval-001": plan_record,
            }
        ),
        implementation_adapter=adapter,
    )

    output = use_case.execute(
        ExecuteImplementationInput(
            specification_path=specification_path,
            specification_approval_id="spec-approval-001",
            implementation_plan_path=implementation_plan_path,
            implementation_plan_approval_id="plan-approval-001",
            codex_prompt="implement approved scope",
            codex_prompt_specification_path=specification_path,
            codex_prompt_implementation_plan_path=implementation_plan_path,
            implementation_branch="developer",
            base_commit="abc123",
            working_directory=tmp_path,
            state_file=state_file,
            state_history_dir=tmp_path / "state_history",
        )
    )

    assert adapter.call_count == 0
    assert output.success is False
    assert output.current_state == "plan_approved"
    assert output.technical_retry_required is False
    assert output.critical_change_required is False
    assert output.stop_reason == "Implementation is not ready."

    current_state = state_file.read_text(encoding="utf-8")
    assert '"status": "plan_approved"' in current_state
