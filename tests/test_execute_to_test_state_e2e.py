import json
from pathlib import Path
from uuid import uuid4
from unittest.mock import Mock

from application.collect_implementation_evidence import CollectImplementationEvidenceUseCase
from application.dto import CollectImplementationEvidenceInput
from application.repository_state_provider import RepositoryState, RepositoryStateProvider
from infrastructure.json_implementation_evidence_repository import JsonImplementationEvidenceRepository

from application.codex_implementation_adapter import (
    CodexImplementationAdapter,
)
from application.dto import ExecuteImplementationInput
from application.execute_implementation import (
    ExecuteImplementationUseCase,
)
from core.approval_record_service import (
    build_approval_record_from_artifact,
)
from infrastructure.codex_jsonl_parser import (
    parse_codex_jsonl,
)
from infrastructure.json_command_trace_repository import (
    JsonCommandTraceRepository,
)
from infrastructure.json_test_execution_record_repository import (
    JsonTestExecutionRecordRepository,
)
from infrastructure.json_test_execution_recorder import (
    JsonTestExecutionRecorder,
)
from infrastructure.json_test_state_provider import (
    JsonTestStateProvider,
)


class FakeApprovalRecordRepository:
    def __init__(
        self,
        records: dict[str, dict],
    ) -> None:
        self._records = records

    def get(
        self,
        approval_id: str,
    ) -> dict | None:
        return self._records.get(approval_id)


class JsonlCodexRunner:
    def run(
        self,
        *,
        prompt: str,
        working_directory: Path,
    ) -> str:
        report = """## Implementation Summary
TEST_REQUIRED: YES
Approved scope implementation completed.

## Changed Files
application/example.py

## Executed Commands
specflow-test commands executed.

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

        commands = (
            (
                "item_initial",
                "initial",
                1,
                "1 failed\n",
            ),
            (
                "item_target",
                "target",
                0,
                "1 passed\n",
            ),
            (
                "item_full",
                "full",
                0,
                "422 passed\n",
            ),
        )

        events = [
            {
                "type": "thread.started",
                "thread_id": "thread-e2e",
            },
            {
                "type": "turn.started",
            },
        ]

        for (
            item_id,
            phase,
            exit_code,
            output,
        ) in commands:
            events.append(
                {
                    "type": "item.completed",
                    "item": {
                        "id": item_id,
                        "type": "command_execution",
                        "command": (
                            "specflow-test "
                            f"--phase {phase} -- "
                            "python -m pytest"
                        ),
                        "aggregated_output": output,
                        "exit_code": exit_code,
                        "status": "completed",
                    },
                }
            )

        events.extend(
            (
                {
                    "type": "item.completed",
                    "item": {
                        "id": "item_report",
                        "type": "agent_message",
                        "text": report,
                    },
                },
                {
                    "type": "turn.completed",
                    "usage": {},
                },
            )
        )

        return "\n".join(
            json.dumps(event)
            for event in events
        )


def test_phase_3_record_is_verified_by_phase_4_provider(
    tmp_path: Path,
) -> None:
    implementation_id = uuid4()
    specification_path = (
        tmp_path / "specification.md"
    )
    plan_path = (
        tmp_path / "implementation_plan.md"
    )
    state_file = tmp_path / "state.json"
    evidence_dir = tmp_path / "evidence"

    specification_path.write_text(
        "approved specification",
        encoding="utf-8",
    )
    plan_path.write_text(
        "approved implementation plan",
        encoding="utf-8",
    )
    state_file.write_text(
        '{"status": "implementation_ready"}',
        encoding="utf-8",
    )

    specification_record = (
        build_approval_record_from_artifact(
            approval_id="spec-approval-e2e",
            artifact_type="specification",
            artifact_path=str(
                specification_path
            ),
            decision="approved",
            approved_at=(
                "2026-09-21T09:00:00+09:00"
            ),
            comment="Specification approved.",
        )
    )
    plan_record = (
        build_approval_record_from_artifact(
            approval_id="plan-approval-e2e",
            artifact_type="implementation_plan",
            artifact_path=str(plan_path),
            decision="approved",
            approved_at=(
                "2026-09-21T09:01:00+09:00"
            ),
            comment="Plan approved.",
        )
    )

    adapter = CodexImplementationAdapter(
        JsonlCodexRunner(),
        trace_parser=parse_codex_jsonl,
    )
    recorder = JsonTestExecutionRecorder(
        trace_repository=(
            JsonCommandTraceRepository(
                evidence_dir=evidence_dir
            )
        ),
        record_repository=(
            JsonTestExecutionRecordRepository(
                evidence_dir=evidence_dir
            )
        ),
    )
    use_case = ExecuteImplementationUseCase(
        approval_repository=(
            FakeApprovalRecordRepository(
                {
                    "spec-approval-e2e": (
                        specification_record
                    ),
                    "plan-approval-e2e": (
                        plan_record
                    ),
                }
            )
        ),
        implementation_adapter=adapter,
        test_execution_recorder=recorder,
    )

    output = use_case.execute(
        ExecuteImplementationInput(
            base_branch="release/baseline",
            implementation_id=implementation_id,
            specification_path=(
                specification_path
            ),
            specification_approval_id=(
                "spec-approval-e2e"
            ),
            implementation_plan_path=plan_path,
            implementation_plan_approval_id=(
                "plan-approval-e2e"
            ),
            codex_prompt="implement approved scope",
            codex_prompt_specification_path=(
                specification_path
            ),
            codex_prompt_implementation_plan_path=(
                plan_path
            ),
            implementation_branch="developer",
            base_commit="abc123",
            working_directory=tmp_path,
            state_file=state_file,
            state_history_dir=(
                tmp_path / "state_history"
            ),
        )
    )

    assert output.success is True
    assert output.implementation_id == (
        implementation_id
    )
    assert (
        output.test_execution_record_path
        is not None
    )
    assert (
        output.test_execution_record_path.exists()
    )

    trace_path = (
        evidence_dir
        / (
            "codex_command_trace_"
            f"{implementation_id}.jsonl"
        )
    )
    assert trace_path.exists()

    provider = JsonTestStateProvider(
        record_path=(
            output.test_execution_record_path
        ),
        expected_implementation_id=(
            implementation_id
        ),
    )
    state = provider.get_state()

    assert state.initial_test_status == "COMPLETED"
    assert state.initial_test_result == "FAIL"
    assert state.target_test_status == "COMPLETED"
    assert state.target_test_result == "PASS"
    assert state.full_test_status == "COMPLETED"
    assert state.full_test_result == "PASS"
    assert len(state.test_commands) == 3
    assert state.unavailable_evidence == (
        "tests_created_or_modified",
        "warnings",
    )

    repository_provider = Mock(spec=RepositoryStateProvider)
    repository_provider.get_state.return_value = RepositoryState(
        branch=output.implementation_branch,
        base_commit=output.base_commit,
        git_status="",
        git_diff="",
        created_files=(),
        modified_files=(),
        deleted_files=(),
    )
    evidence_repository = JsonImplementationEvidenceRepository(evidence_dir)
    collected = CollectImplementationEvidenceUseCase(
        repository_state_provider=repository_provider,
        test_state_provider=provider,
        evidence_repository=evidence_repository,
    ).execute(CollectImplementationEvidenceInput(
        base_branch=output.base_branch,
        base_commit=output.base_commit,
        implementation_branch=output.implementation_branch,
        implementation_id=output.implementation_id,
        test_execution_record_path=output.test_execution_record_path,
        implementation_kind="INITIAL",
        previous_evidence_id=None,
        specification_path=output.specification_path,
        specification_approval_id="spec-approval-e2e",
        implementation_plan_path=output.implementation_plan_path,
        implementation_plan_approval_id="plan-approval-e2e",
        codex_prompt_path=tmp_path / "codex_prompt.md",
        codex_prompt="Implement approved scope.",
        implementation_result=output.implementation_result,
        approved_scope=None,
    ))

    assert collected.success is True
    restored = evidence_repository.load(collected.evidence_id)
    assert restored.identity.implementation_id == output.implementation_id
    assert restored.identity.base_branch == "release/baseline"
    assert restored.identity.base_commit == output.base_commit
    assert restored.identity.implementation_branch == output.implementation_branch
    assert restored.verification.test_execution_record_path == output.test_execution_record_path
    assert JsonTestStateProvider(
        record_path=restored.verification.test_execution_record_path,
        expected_implementation_id=restored.identity.implementation_id,
    ).get_state() == state
