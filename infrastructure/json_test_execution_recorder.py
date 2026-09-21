from datetime import datetime
from pathlib import Path
from uuid import UUID

from application.codex_execution import (
    CodexCommandEvent,
)
from application.execution_record_builder import (
    build_test_execution_record,
)
from infrastructure.command_trace_normalizer import (
    normalize_command_trace,
)
from infrastructure.json_command_trace_repository import (
    JsonCommandTraceRepository,
)
from infrastructure.json_test_execution_record_repository import (
    JsonTestExecutionRecordRepository,
)


class JsonTestExecutionRecorder:
    def __init__(
        self,
        *,
        trace_repository: JsonCommandTraceRepository,
        record_repository: (
            JsonTestExecutionRecordRepository
        ),
    ) -> None:
        self._trace_repository = trace_repository
        self._record_repository = record_repository

    def record(
        self,
        *,
        implementation_id: UUID,
        recorded_at: datetime,
        command_events: tuple[
            CodexCommandEvent,
            ...,
        ],
        test_required: bool,
        tests_created_or_modified: tuple[str, ...],
        errors: tuple[str, ...],
        warnings: tuple[str, ...],
        no_tdd_reason: str | None,
        unavailable_evidence: tuple[str, ...] = (),
    ) -> Path:
        normalized_trace = normalize_command_trace(
            command_events
        )

        saved_trace = self._trace_repository.save(
            implementation_id,
            normalized_trace,
        )

        record = build_test_execution_record(
            implementation_id=implementation_id,
            recorded_at=recorded_at,
            command_events=command_events,
            test_required=test_required,
            tests_created_or_modified=(
                tests_created_or_modified
            ),
            command_trace_path=saved_trace.path,
            command_trace_sha256=(
                saved_trace.sha256
            ),
            errors=errors,
            warnings=warnings,
            no_tdd_reason=no_tdd_reason,
            unavailable_evidence=(
                unavailable_evidence
            ),
        )

        return self._record_repository.save(
            record
        )
