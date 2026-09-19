import hashlib
import json
from pathlib import Path
from uuid import UUID

from application.execution_record_serializer import (
    execution_record_from_dict,
)
from application.execution_state_provider import (
    TestState,
)


class JsonTestStateProvider:
    def __init__(
        self,
        *,
        record_path: Path,
        expected_implementation_id: UUID,
    ) -> None:
        self._record_path = record_path
        self._expected_implementation_id = (
            expected_implementation_id
        )

    def get_state(self) -> TestState:
        data = json.loads(
            self._record_path.read_text(
                encoding="utf-8"
            )
        )

        if not isinstance(data, dict):
            raise ValueError(
                "Test Execution Record must be "
                "a JSON object."
            )

        record = execution_record_from_dict(data)

        if (
            record.implementation_id
            != self._expected_implementation_id
        ):
            raise ValueError(
                "Test Execution Record implementation_id "
                "does not match the expected "
                "implementation_id."
            )

        trace_path = record.command_trace_path
        expected_trace_name = (
            "codex_command_trace_"
            f"{record.implementation_id}.jsonl"
        )

        if trace_path.name != expected_trace_name:
            raise ValueError(
                "Invalid command trace path: "
                "filename does not match the "
                "Test Execution Record "
                "implementation_id."
            )

        expected_trace_directory = (
            self._record_path.parent.resolve()
        )
        actual_trace_directory = (
            trace_path.parent.resolve()
        )

        if (
            actual_trace_directory
            != expected_trace_directory
        ):
            raise ValueError(
                "Invalid command trace path: "
                "trace must be stored in the same "
                "evidence directory as the "
                "Test Execution Record."
            )

        trace_bytes = trace_path.read_bytes()
        actual_sha256 = hashlib.sha256(
            trace_bytes
        ).hexdigest()

        if (
            actual_sha256
            != record.command_trace_sha256
        ):
            raise ValueError(
                "Command trace SHA-256 does not match "
                "the Test Execution Record."
            )

        return TestState(
            tests_created_or_modified=(
                record.tests_created_or_modified
            ),
            test_commands=record.test_commands,
            initial_test_status=(
                record.initial_test.status
            ),
            initial_test_result=(
                record.initial_test.result
            ),
            target_test_status=(
                record.target_test.status
            ),
            target_test_result=(
                record.target_test.result
            ),
            full_test_status=record.full_test.status,
            full_test_result=record.full_test.result,
            errors=record.errors,
            warnings=record.warnings,
            unavailable_evidence=(
                record.unavailable_evidence
            ),
            no_tdd_reason=record.no_tdd_reason,
        )
