import json
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
from infrastructure.json_implementation_evidence_repository import (
    JsonImplementationEvidenceRepository,
)


def make_evidence() -> ImplementationEvidence:
    evidence_id = uuid4()

    return ImplementationEvidence(
        identity=EvidenceIdentity(
            evidence_id=evidence_id,
            implementation_id=uuid4(),
            implementation_kind="INITIAL",
            previous_evidence_id=None,
            status="COLLECTED",
            created_at=datetime(
                2026,
                9,
                12,
                9,
                30,
                tzinfo=timezone.utc,
            ),
        ),
        basis=EvidenceBasis(
            specification_path=Path("specification.md"),
            specification_hash="spec-hash",
            specification_approval_id="spec-approval",
            implementation_plan_path=Path(
                "implementation_plan.md"
            ),
            implementation_plan_hash="plan-hash",
            implementation_plan_approval_id="plan-approval",
            codex_prompt_path=Path("codex_prompt.md"),
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
            git_diff_path=Path(
                f"evidence/implementation_{evidence_id}.diff"
            ),
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
            implementation_result=ImplementationResult(
                implementation_summary="completed",
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
            ),
        ),
    )


def test_save_creates_canonical_json_file(tmp_path: Path) -> None:
    repository = JsonImplementationEvidenceRepository(
        tmp_path / "evidence"
    )
    evidence = make_evidence()

    saved_path = repository.save(evidence)

    expected_path = (
        tmp_path
        / "evidence"
        / f"implementation_{evidence.identity.evidence_id}.json"
    )

    assert saved_path == expected_path
    assert saved_path.exists()

    data = json.loads(
        saved_path.read_text(encoding="utf-8")
    )

    assert data["identity"]["evidence_id"] == str(
        evidence.identity.evidence_id
    )


def test_exists_reports_saved_evidence(tmp_path: Path) -> None:
    repository = JsonImplementationEvidenceRepository(
        tmp_path / "evidence"
    )
    evidence = make_evidence()

    assert repository.exists(
        evidence.identity.evidence_id
    ) is False

    repository.save(evidence)

    assert repository.exists(
        evidence.identity.evidence_id
    ) is True


def test_load_restores_saved_evidence(tmp_path: Path) -> None:
    repository = JsonImplementationEvidenceRepository(
        tmp_path / "evidence"
    )
    evidence = make_evidence()

    repository.save(evidence)

    restored = repository.load(
        evidence.identity.evidence_id
    )

    assert restored == evidence


def test_load_missing_evidence_raises_file_not_found(
    tmp_path: Path,
) -> None:
    repository = JsonImplementationEvidenceRepository(
        tmp_path / "evidence"
    )

    with pytest.raises(FileNotFoundError):
        repository.load(uuid4())


def test_save_refuses_to_overwrite_existing_evidence(
    tmp_path: Path,
) -> None:
    repository = JsonImplementationEvidenceRepository(
        tmp_path / "evidence"
    )
    evidence = make_evidence()

    repository.save(evidence)

    with pytest.raises(FileExistsError):
        repository.save(evidence)


def test_save_diff_creates_canonical_diff_file(
    tmp_path: Path,
) -> None:
    repository = JsonImplementationEvidenceRepository(
        tmp_path / "evidence"
    )
    evidence_id = uuid4()
    diff = "diff --git a/example.py b/example.py\n"

    saved_path = repository.save_diff(
        evidence_id,
        diff,
    )

    expected_path = (
        tmp_path
        / "evidence"
        / f"implementation_{evidence_id}.diff"
    )

    assert saved_path == expected_path
    assert saved_path.read_text(encoding="utf-8") == diff


def test_save_diff_refuses_to_overwrite_existing_diff(
    tmp_path: Path,
) -> None:
    repository = JsonImplementationEvidenceRepository(
        tmp_path / "evidence"
    )
    evidence_id = uuid4()

    repository.save_diff(
        evidence_id,
        "first diff\n",
    )

    with pytest.raises(FileExistsError):
        repository.save_diff(
            evidence_id,
            "second diff\n",
        )
