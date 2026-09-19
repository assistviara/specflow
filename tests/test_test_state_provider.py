from dataclasses import FrozenInstanceError
from typing import Protocol

import pytest

from application.execution_state_provider import (
    TestState as State,
    TestStateProvider as StateProvider,
)


def test_test_state_is_frozen_dataclass() -> None:
    state = State(
        tests_created_or_modified=(
            "tests/test_example.py",
        ),
        test_commands=(
            "python -m pytest tests/test_example.py",
            "python -m pytest",
        ),
        initial_test_status="COMPLETED",
        initial_test_result="FAIL",
        target_test_status="COMPLETED",
        target_test_result="PASS",
        full_test_status="COMPLETED",
        full_test_result="PASS",
        errors=(),
        warnings=(),
    )

    assert state.tests_created_or_modified == (
        "tests/test_example.py",
    )
    assert state.initial_test_result == "FAIL"
    assert state.target_test_result == "PASS"
    assert state.full_test_result == "PASS"

    with pytest.raises(FrozenInstanceError):
        state.full_test_result = "FAIL"


@pytest.mark.parametrize(
    ("status", "result"),
    [
        ("COMPLETED", "PASS"),
        ("COMPLETED", "FAIL"),
        ("ERROR", "NONE"),
        ("NOT_RUN", "NONE"),
    ],
)
def test_test_state_accepts_valid_status_result_pairs(
    status: str,
    result: str,
) -> None:
    state = State(
        tests_created_or_modified=(),
        test_commands=(),
        initial_test_status=status,
        initial_test_result=result,
        target_test_status=status,
        target_test_result=result,
        full_test_status=status,
        full_test_result=result,
        errors=(),
        warnings=(),
    )

    assert state.initial_test_status == status
    assert state.initial_test_result == result


@pytest.mark.parametrize(
    ("status", "result"),
    [
        ("COMPLETED", "NONE"),
        ("ERROR", "PASS"),
        ("ERROR", "FAIL"),
        ("NOT_RUN", "PASS"),
        ("NOT_RUN", "FAIL"),
        ("UNKNOWN", "NONE"),
    ],
)
def test_test_state_rejects_invalid_status_result_pairs(
    status: str,
    result: str,
) -> None:
    with pytest.raises(ValueError):
        State(
            tests_created_or_modified=(),
            test_commands=(),
            initial_test_status=status,
            initial_test_result=result,
            target_test_status="NOT_RUN",
            target_test_result="NONE",
            full_test_status="NOT_RUN",
            full_test_result="NONE",
            errors=(),
            warnings=(),
        )


def test_test_state_can_preserve_unavailable_records() -> None:
    state = State(
        tests_created_or_modified=(),
        test_commands=(),
        initial_test_status="NOT_RUN",
        initial_test_result="NONE",
        target_test_status="NOT_RUN",
        target_test_result="NONE",
        full_test_status="NOT_RUN",
        full_test_result="NONE",
        errors=(),
        warnings=(
            "initial RED execution record unavailable",
        ),
    )

    assert state.initial_test_status == "NOT_RUN"
    assert state.initial_test_result == "NONE"
    assert state.warnings == (
        "initial RED execution record unavailable",
    )


def test_test_state_provider_is_protocol() -> None:
    assert issubclass(
        StateProvider,
        Protocol,
    )


def test_test_state_provider_exposes_get_state() -> None:
    assert "get_state" in StateProvider.__dict__


def test_test_state_preserves_unavailable_evidence() -> None:
    state = State(
        tests_created_or_modified=(),
        test_commands=(),
        initial_test_status="NOT_RUN",
        initial_test_result="NONE",
        target_test_status="COMPLETED",
        target_test_result="PASS",
        full_test_status="COMPLETED",
        full_test_result="PASS",
        errors=(),
        warnings=(),
        unavailable_evidence=("initial_test_result",),
    )

    assert state.initial_test_result == "NONE"
    assert state.unavailable_evidence == (
        "initial_test_result",
    )


def test_test_state_has_optional_no_tdd_reason() -> None:
    from typing import get_type_hints

    hints = get_type_hints(State)

    assert hints["no_tdd_reason"] == str | None


def test_test_state_defaults_no_tdd_reason_to_none() -> None:
    state = State(
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

    assert state.no_tdd_reason is None


def test_test_state_preserves_explicit_no_tdd_reason() -> None:
    state = State(
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
        no_tdd_reason="TDD was explicitly not performed",
    )

    assert state.no_tdd_reason == "TDD was explicitly not performed"
