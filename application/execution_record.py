from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import UUID


@dataclass(frozen=True)
class TestExecutionResult:
    status: str
    result: str

    def __post_init__(self) -> None:
        if self.status not in {
            "COMPLETED",
            "ERROR",
            "NOT_RUN",
        }:
            raise ValueError("invalid test status")

        if self.result not in {
            "PASS",
            "FAIL",
            "NONE",
        }:
            raise ValueError("invalid test result")

        if (
            self.status == "COMPLETED"
            and self.result not in {"PASS", "FAIL"}
        ):
            raise ValueError(
                "COMPLETED test status requires PASS or FAIL"
            )

        if (
            self.status in {"ERROR", "NOT_RUN"}
            and self.result != "NONE"
        ):
            raise ValueError(
                "ERROR or NOT_RUN test status requires NONE"
            )


@dataclass(frozen=True)
class TestExecutionRecord:
    schema_version: str
    implementation_id: UUID
    recorded_at: datetime
    tests_created_or_modified: tuple[str, ...]
    test_commands: tuple[str, ...]
    initial_test: TestExecutionResult
    target_test: TestExecutionResult
    full_test: TestExecutionResult
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    unavailable_evidence: tuple[str, ...]
    no_tdd_reason: str | None
    command_trace_path: Path
    command_trace_sha256: str

    def __post_init__(self) -> None:
        if self.schema_version != "1":
            raise ValueError(
                'schema_version must be "1"'
            )

        if not isinstance(self.implementation_id, UUID):
            raise ValueError(
                "implementation_id must be UUID"
            )

        if not isinstance(self.recorded_at, datetime):
            raise ValueError(
                "recorded_at must be datetime"
            )

        if (
            self.recorded_at.tzinfo is None
            or self.recorded_at.utcoffset() is None
        ):
            raise ValueError(
                "recorded_at must be timezone-aware"
            )

        string_tuple_fields = {
            "tests_created_or_modified": (
                self.tests_created_or_modified
            ),
            "test_commands": self.test_commands,
            "errors": self.errors,
            "warnings": self.warnings,
            "unavailable_evidence": (
                self.unavailable_evidence
            ),
        }

        for field_name, value in string_tuple_fields.items():
            if (
                not isinstance(value, tuple)
                or not all(
                    isinstance(item, str)
                    for item in value
                )
            ):
                raise ValueError(
                    f"{field_name} must be tuple[str, ...]"
                )

        if (
            self.no_tdd_reason is not None
            and not isinstance(self.no_tdd_reason, str)
        ):
            raise ValueError(
                "no_tdd_reason must be str or None"
            )

        if not isinstance(self.command_trace_path, Path):
            raise ValueError(
                "command_trace_path must be Path"
            )

        if (
            not isinstance(self.command_trace_sha256, str)
            or len(self.command_trace_sha256) != 64
        ):
            raise ValueError(
                "command_trace_sha256 must be a SHA-256 hash"
            )

        try:
            int(self.command_trace_sha256, 16)
        except ValueError as error:
            raise ValueError(
                "command_trace_sha256 must be a SHA-256 hash"
            ) from error
