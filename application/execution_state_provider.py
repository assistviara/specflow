from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class TestState:
    tests_created_or_modified: tuple[str, ...]
    test_commands: tuple[str, ...]
    initial_test_status: str
    initial_test_result: str
    target_test_status: str
    target_test_result: str
    full_test_status: str
    full_test_result: str
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    unavailable_evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        pairs = (
            (
                self.initial_test_status,
                self.initial_test_result,
            ),
            (
                self.target_test_status,
                self.target_test_result,
            ),
            (
                self.full_test_status,
                self.full_test_result,
            ),
        )

        for status, result in pairs:
            if status not in {
                "COMPLETED",
                "ERROR",
                "NOT_RUN",
            }:
                raise ValueError("invalid test status")

            if result not in {
                "PASS",
                "FAIL",
                "NONE",
            }:
                raise ValueError("invalid test result")

            if (
                status == "COMPLETED"
                and result not in {"PASS", "FAIL"}
            ):
                raise ValueError(
                    "COMPLETED test status requires PASS or FAIL"
                )

            if (
                status in {"ERROR", "NOT_RUN"}
                and result != "NONE"
            ):
                raise ValueError(
                    "ERROR or NOT_RUN test status requires NONE"
                )


class TestStateProvider(Protocol):
    def get_state(self) -> TestState:
        ...
