from dataclasses import FrozenInstanceError

import pytest

from application.implementation_evidence import EvidenceVerification


def test_evidence_verification_is_frozen_dataclass() -> None:
    verification = EvidenceVerification(
        commands=("python -m pytest tests/test_example.py",),
        tests_created_or_modified=("tests/test_example.py",),
        test_commands=("python -m pytest tests/test_example.py",),
        initial_test_status="COMPLETED",
        initial_test_result="FAIL",
        target_test_status="COMPLETED",
        target_test_result="PASS",
        full_test_status="COMPLETED",
        full_test_result="PASS",
        errors=(),
        warnings=(),
        no_tdd_reason=None,
    )

    assert verification.commands == (
        "python -m pytest tests/test_example.py",
    )
    assert verification.tests_created_or_modified == (
        "tests/test_example.py",
    )
    assert verification.initial_test_status == "COMPLETED"
    assert verification.initial_test_result == "FAIL"
    assert verification.target_test_result == "PASS"
    assert verification.full_test_result == "PASS"
    assert verification.no_tdd_reason is None

    with pytest.raises(FrozenInstanceError):
        verification.full_test_result = "FAIL"


@pytest.mark.parametrize(
    "field_name",
    [
        "initial_test_status",
        "target_test_status",
        "full_test_status",
    ],
)
def test_evidence_verification_rejects_invalid_test_status(
    field_name: str,
) -> None:
    values = {
        "commands": (),
        "tests_created_or_modified": (),
        "test_commands": (),
        "initial_test_status": "NOT_RUN",
        "initial_test_result": "NONE",
        "target_test_status": "NOT_RUN",
        "target_test_result": "NONE",
        "full_test_status": "NOT_RUN",
        "full_test_result": "NONE",
        "errors": (),
        "warnings": (),
        "no_tdd_reason": None,
    }

    values[field_name] = "UNKNOWN"

    with pytest.raises(ValueError):
        EvidenceVerification(**values)


@pytest.mark.parametrize(
    "field_name",
    [
        "initial_test_result",
        "target_test_result",
        "full_test_result",
    ],
)
def test_evidence_verification_rejects_invalid_test_result(
    field_name: str,
) -> None:
    values = {
        "commands": (),
        "tests_created_or_modified": (),
        "test_commands": (),
        "initial_test_status": "NOT_RUN",
        "initial_test_result": "NONE",
        "target_test_status": "NOT_RUN",
        "target_test_result": "NONE",
        "full_test_status": "NOT_RUN",
        "full_test_result": "NONE",
        "errors": (),
        "warnings": (),
        "no_tdd_reason": None,
    }

    values[field_name] = "UNKNOWN"

    with pytest.raises(ValueError):
        EvidenceVerification(**values)


@pytest.mark.parametrize(
    ("status", "result"),
    [
        ("COMPLETED", "NONE"),
        ("ERROR", "PASS"),
        ("ERROR", "FAIL"),
        ("NOT_RUN", "PASS"),
        ("NOT_RUN", "FAIL"),
    ],
)
def test_evidence_verification_rejects_invalid_status_result_pair(
    status: str,
    result: str,
) -> None:
    with pytest.raises(ValueError):
        EvidenceVerification(
            commands=(),
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
            no_tdd_reason=None,
        )


@pytest.mark.parametrize(
    ("status", "result"),
    [
        ("COMPLETED", "PASS"),
        ("COMPLETED", "FAIL"),
        ("ERROR", "NONE"),
        ("NOT_RUN", "NONE"),
    ],
)
def test_evidence_verification_accepts_valid_status_result_pair(
    status: str,
    result: str,
) -> None:
    verification = EvidenceVerification(
        commands=(),
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
        no_tdd_reason=None,
    )

    assert verification.initial_test_status == status
    assert verification.initial_test_result == result
