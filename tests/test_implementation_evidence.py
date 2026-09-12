from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from application.implementation_evidence import (
    EvidenceBasis,
    EvidenceChanges,
    EvidenceCodexSummary,
    EvidenceDeviations,
    EvidenceIdentity,
    EvidenceScope,
    EvidenceVerification,
    ImplementationEvidence,
)
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


def test_implementation_evidence_is_frozen_dataclass_with_typed_blocks() -> None:
    evidence = ImplementationEvidence(
        identity=EvidenceIdentity(
            evidence_id=uuid4(),
            implementation_id=uuid4(),
            implementation_kind="INITIAL",
            previous_evidence_id=None,
            status="COLLECTED",
            created_at=datetime(
                2026,
                9,
                12,
                8,
                30,
                tzinfo=timezone.utc,
            ),
        ),
        basis=EvidenceBasis(
            specification_path=Path("spec.md"),
            specification_hash="spec-hash",
            specification_approval_id="spec-approval-1",
            implementation_plan_path=Path("plan.md"),
            implementation_plan_hash="plan-hash",
            implementation_plan_approval_id="plan-approval-1",
            codex_prompt_path=Path("prompt.md"),
            codex_prompt_hash="prompt-hash",
        ),
        scope=EvidenceScope(
            target_paths=("application/**",),
            allowed_changes=("application/**",),
            forbidden_changes=("core/**",),
        ),
        changes=EvidenceChanges(
            created_files=("application/example.py",),
            modified_files=(),
            deleted_files=(),
            git_diff_path=Path("evidence/example.diff"),
            change_summary="example change",
        ),
        verification=EvidenceVerification(
            commands=("python -m pytest",),
            tests_created_or_modified=("tests/test_example.py",),
            test_commands=("python -m pytest",),
            initial_test_status="COMPLETED",
            initial_test_result="FAIL",
            target_test_status="COMPLETED",
            target_test_result="PASS",
            full_test_status="COMPLETED",
            full_test_result="PASS",
            errors=(),
            warnings=(),
            no_tdd_reason=None,
        ),
        deviations=EvidenceDeviations(
            out_of_scope_changes=(),
            unplanned_changes=(),
            unfinished_items=(),
            human_approval_required=(),
        ),
        codex_summary=EvidenceCodexSummary(
            implementation_result=make_implementation_result(),
        ),
    )

    assert isinstance(evidence.identity, EvidenceIdentity)
    assert isinstance(evidence.basis, EvidenceBasis)
    assert isinstance(evidence.scope, EvidenceScope)
    assert isinstance(evidence.changes, EvidenceChanges)
    assert isinstance(evidence.verification, EvidenceVerification)
    assert isinstance(evidence.deviations, EvidenceDeviations)
    assert isinstance(evidence.codex_summary, EvidenceCodexSummary)

    with pytest.raises(FrozenInstanceError):
        evidence.scope = EvidenceScope(
            target_paths=(),
            allowed_changes=(),
            forbidden_changes=(),
        )
