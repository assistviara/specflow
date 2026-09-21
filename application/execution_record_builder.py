from datetime import datetime
from pathlib import Path
from uuid import UUID

from application.codex_execution import (
    CodexCommandEvent,
)
from application.execution_record import (
    TestExecutionRecord,
    TestExecutionResult,
)


def _build_phase_result(
    command_events: tuple[
        CodexCommandEvent,
        ...,
    ],
    phase: str,
) -> TestExecutionResult:
    phase_events = tuple(
        event
        for event in command_events
        if event.test_phase == phase
    )

    if not phase_events:
        return TestExecutionResult(
            status="NOT_RUN",
            result="NONE",
        )

    if any(
        event.status != "completed"
        or event.exit_code is None
        for event in phase_events
    ):
        return TestExecutionResult(
            status="ERROR",
            result="NONE",
        )

    if any(
        event.exit_code != 0
        for event in phase_events
    ):
        return TestExecutionResult(
            status="COMPLETED",
            result="FAIL",
        )

    return TestExecutionResult(
        status="COMPLETED",
        result="PASS",
    )


def build_test_execution_record(
    *,
    implementation_id: UUID,
    recorded_at: datetime,
    command_events: tuple[
        CodexCommandEvent,
        ...,
    ],
    test_required: bool,
    tests_created_or_modified: tuple[str, ...],
    command_trace_path: Path,
    command_trace_sha256: str,
    errors: tuple[str, ...],
    warnings: tuple[str, ...],
    no_tdd_reason: str | None,
    unavailable_evidence: tuple[str, ...] = (),
) -> TestExecutionRecord:
    test_commands = tuple(
        event.command
        for event in command_events
        if event.test_phase is not None
    )

    unavailable_phase_evidence = (
        tuple(
            f"{phase}_test_result"
            for phase in (
                "initial",
                "target",
                "full",
            )
            if not any(
                event.test_phase == phase
                for event in command_events
            )
        )
        if test_required
        else ()
    )

    combined_unavailable_evidence = tuple(
        dict.fromkeys(
            (
                *unavailable_evidence,
                *unavailable_phase_evidence,
            )
        )
    )

    return TestExecutionRecord(
        schema_version="1",
        implementation_id=implementation_id,
        recorded_at=recorded_at,
        tests_created_or_modified=(
            tests_created_or_modified
        ),
        test_commands=test_commands,
        initial_test=_build_phase_result(
            command_events,
            "initial",
        ),
        target_test=_build_phase_result(
            command_events,
            "target",
        ),
        full_test=_build_phase_result(
            command_events,
            "full",
        ),
        errors=errors,
        warnings=warnings,
        unavailable_evidence=(
            combined_unavailable_evidence
        ),
        no_tdd_reason=no_tdd_reason,
        command_trace_path=command_trace_path,
        command_trace_sha256=(
            command_trace_sha256
        ),
    )
