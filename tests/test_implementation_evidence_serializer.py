from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

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
from application.implementation_evidence_serializer import (
    implementation_evidence_from_dict,
    implementation_evidence_to_dict,
)
from application.implementation_result_parser import ImplementationResult


def make_evidence() -> ImplementationEvidence:
    evidence_id = uuid4()
    implementation_id = uuid4()

    implementation_result = ImplementationResult(
        implementation_summary="Implementation completed",
        changed_files="application/example.py",
        executed_commands="python -m pytest",
        test_execution_status="COMPLETED",
        test_result="PASS",
        test_execution_error="NONE",
        errors="NONE",
        warnings="NONE",
        incomplete_items="NONE",
        human_approval_required="NONE",
        test_required=True,
        technical_retry_safe=False,
        technical_retry_operation=None,
    )

    return ImplementationEvidence(
        identity=EvidenceIdentity(
            evidence_id=evidence_id,
            implementation_id=implementation_id,
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
            specification_path=Path(
                "projects/specflow/specification.md"
            ),
            specification_hash="spec-hash",
            specification_approval_id="spec-approval",
            implementation_plan_path=Path(
                "projects/specflow/implementation_plan.md"
            ),
            implementation_plan_hash="plan-hash",
            implementation_plan_approval_id="plan-approval",
            codex_prompt_path=Path(
                "projects/specflow/codex_prompt.md"
            ),
            codex_prompt_hash="prompt-hash",
        ),
        scope=EvidenceScope(
            target_paths=("application/**", "tests/**"),
            allowed_changes=("application/**", "tests/**"),
            forbidden_changes=("core/**",),
        ),
        changes=EvidenceChanges(
            created_files=("application/example.py",),
            modified_files=("tests/test_example.py",),
            deleted_files=(),
            git_diff_path=Path(
                f"evidence/implementation_{evidence_id}.diff"
            ),
            change_summary="Implementation Evidence example",
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
            warnings=("example warning",),
            no_tdd_reason=None,
        ),
        deviations=EvidenceDeviations(
            out_of_scope_changes=(),
            unplanned_changes=(),
            unfinished_items=(),
            human_approval_required=(),
        ),
        codex_summary=EvidenceCodexSummary(
            implementation_result=implementation_result,
        ),
    )


def test_implementation_evidence_to_dict_uses_json_safe_values() -> None:
    evidence = make_evidence()

    data = implementation_evidence_to_dict(evidence)

    assert data["identity"]["evidence_id"] == str(
        evidence.identity.evidence_id
    )
    assert data["identity"]["implementation_id"] == str(
        evidence.identity.implementation_id
    )
    assert data["identity"]["previous_evidence_id"] is None
    assert data["identity"]["created_at"] == (
        "2026-09-12T08:30:00+00:00"
    )

    assert data["basis"]["specification_path"] == (
        "projects/specflow/specification.md"
    )

    assert data["scope"]["target_paths"] == [
        "application/**",
        "tests/**",
    ]

    assert data["changes"]["git_diff_path"].startswith(
        "evidence/"
    )

    assert data["verification"]["warnings"] == [
        "example warning"
    ]

    assert (
        data["codex_summary"]["implementation_result"]["test_result"]
        == "PASS"
    )


def test_implementation_evidence_round_trip_restores_types() -> None:
    evidence = make_evidence()

    restored = implementation_evidence_from_dict(
        implementation_evidence_to_dict(evidence)
    )

    assert restored == evidence

    assert isinstance(
        restored.identity.evidence_id,
        UUID,
    )
    assert isinstance(
        restored.identity.created_at,
        datetime,
    )
    assert isinstance(
        restored.basis.specification_path,
        Path,
    )
    assert isinstance(
        restored.scope.target_paths,
        tuple,
    )
    assert isinstance(
        restored.verification.warnings,
        tuple,
    )
    assert isinstance(
        restored.codex_summary.implementation_result,
        ImplementationResult,
    )


def test_implementation_evidence_round_trip_preserves_none_scope() -> None:
    from dataclasses import replace

    evidence = replace(
        make_evidence(),
        scope=None,
    )

    data = implementation_evidence_to_dict(evidence)

    assert data["scope"] is None

    restored = implementation_evidence_from_dict(data)

    assert restored.scope is None
    assert restored == evidence


def test_implementation_evidence_round_trip_preserves_none_implementation_result() -> None:
    from dataclasses import replace

    evidence = make_evidence()

    evidence = replace(
        evidence,
        codex_summary=EvidenceCodexSummary(
            implementation_result=None,
        ),
    )

    data = implementation_evidence_to_dict(evidence)

    assert data["codex_summary"]["implementation_result"] is None

    restored = implementation_evidence_from_dict(data)

    assert restored.codex_summary.implementation_result is None
    assert restored == evidence
