import hashlib
from pathlib import Path

from application.dto import CollectImplementationEvidenceInput
from application.implementation_evidence_basis_builder import (
    ImplementationEvidenceBasisBuilder,
)


def _make_input(
    tmp_path: Path,
    *,
    codex_prompt: str = "Implement approved scope.",
) -> CollectImplementationEvidenceInput:
    from uuid import uuid4

    specification_path = tmp_path / "specification.md"
    implementation_plan_path = tmp_path / "implementation_plan.md"
    codex_prompt_path = tmp_path / "codex_prompt.md"

    specification_path.write_bytes(b"specification bytes")
    implementation_plan_path.write_bytes(b"implementation plan bytes")

    # Prompt fileの現在内容は、実際に送信した本文とは意図的に変える。
    codex_prompt_path.write_text(
        "CURRENT FILE CONTENT",
        encoding="utf-8",
    )

    return CollectImplementationEvidenceInput(
        implementation_id=uuid4(),
        implementation_kind="INITIAL",
        previous_evidence_id=None,
        specification_path=specification_path,
        specification_approval_id="spec-approval-001",
        implementation_plan_path=implementation_plan_path,
        implementation_plan_approval_id="plan-approval-001",
        codex_prompt_path=codex_prompt_path,
        codex_prompt=codex_prompt,
        implementation_branch="developer",
        base_commit="abc123",
        implementation_result=None,
        approved_scope=None,
    )


def test_build_hashes_specification_from_actual_file_bytes(
    tmp_path: Path,
) -> None:
    input_dto = _make_input(tmp_path)

    result = ImplementationEvidenceBasisBuilder().build(input_dto)
    basis = result.basis

    expected = hashlib.sha256(
        b"specification bytes"
    ).hexdigest()

    assert basis.specification_hash == expected


def test_build_hashes_plan_from_actual_file_bytes(
    tmp_path: Path,
) -> None:
    input_dto = _make_input(tmp_path)

    result = ImplementationEvidenceBasisBuilder().build(input_dto)
    basis = result.basis

    expected = hashlib.sha256(
        b"implementation plan bytes"
    ).hexdigest()

    assert basis.implementation_plan_hash == expected


def test_build_hashes_prompt_from_exact_sent_body_not_current_file(
    tmp_path: Path,
) -> None:
    sent_prompt = "Implement approved scope."
    input_dto = _make_input(
        tmp_path,
        codex_prompt=sent_prompt,
    )

    result = ImplementationEvidenceBasisBuilder().build(input_dto)
    basis = result.basis

    expected = hashlib.sha256(
        sent_prompt.encode("utf-8")
    ).hexdigest()

    current_file_hash = hashlib.sha256(
        input_dto.codex_prompt_path.read_bytes()
    ).hexdigest()

    assert basis.codex_prompt_hash == expected
    assert basis.codex_prompt_hash != current_file_hash


def test_build_preserves_basis_identity(
    tmp_path: Path,
) -> None:
    input_dto = _make_input(tmp_path)

    result = ImplementationEvidenceBasisBuilder().build(input_dto)
    basis = result.basis

    assert basis.specification_path == input_dto.specification_path
    assert (
        basis.specification_approval_id
        == input_dto.specification_approval_id
    )
    assert (
        basis.implementation_plan_path
        == input_dto.implementation_plan_path
    )
    assert (
        basis.implementation_plan_approval_id
        == input_dto.implementation_plan_approval_id
    )
    assert basis.codex_prompt_path == input_dto.codex_prompt_path


def test_build_returns_missing_evidence_when_specification_is_unavailable(
    tmp_path: Path,
) -> None:
    input_dto = _make_input(tmp_path)

    input_dto.specification_path.unlink()

    result = ImplementationEvidenceBasisBuilder().build(input_dto)

    assert result.basis.specification_hash is None
    assert result.basis.implementation_plan_hash is not None
    assert result.basis.codex_prompt_hash is not None
    assert "specification hash unavailable" in result.missing_evidence
    assert "failed to read specification for hashing" in result.errors


def test_build_returns_missing_evidence_when_plan_is_unavailable(
    tmp_path: Path,
) -> None:
    input_dto = _make_input(tmp_path)

    input_dto.implementation_plan_path.unlink()

    result = ImplementationEvidenceBasisBuilder().build(input_dto)

    assert result.basis.specification_hash is not None
    assert result.basis.implementation_plan_hash is None
    assert result.basis.codex_prompt_hash is not None
    assert "implementation plan hash unavailable" in result.missing_evidence
    assert "failed to read implementation plan for hashing" in result.errors
