from dataclasses import FrozenInstanceError

import pytest

from application.implementation_evidence import EvidenceCodexSummary
from application.implementation_result_parser import ImplementationResult


def make_implementation_result() -> ImplementationResult:
    return ImplementationResult(
        implementation_summary=(
            "TEST_REQUIRED: YES\n"
            "Implementation Evidenceを実装"
        ),
        changed_files="application/example.py",
        executed_commands="python -m pytest",
        test_execution_status="COMPLETED",
        test_result="PASS",
        test_execution_error=(
            "TECHNICAL_RETRY_SAFE: NO\n"
            "TECHNICAL_RETRY_OPERATION: NONE"
        ),
        errors="NONE",
        warnings="NONE",
        incomplete_items="NONE",
        human_approval_required="NONE",
        test_required=True,
        technical_retry_safe=False,
        technical_retry_operation=None,
    )


def test_evidence_codex_summary_is_frozen_dataclass() -> None:
    implementation_result = make_implementation_result()

    summary = EvidenceCodexSummary(
        implementation_result=implementation_result,
    )

    assert summary.implementation_result is implementation_result
    assert summary.implementation_result.test_result == "PASS"
    assert summary.implementation_result.changed_files == (
        "application/example.py"
    )

    with pytest.raises(FrozenInstanceError):
        summary.implementation_result = make_implementation_result()
