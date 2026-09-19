from dataclasses import FrozenInstanceError
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from application.implementation_evidence import ImplementationEvidence

from application.dto import (
    CollectImplementationEvidenceInput,
    CollectImplementationEvidenceOutput,
)


def test_collect_implementation_evidence_input_is_frozen_dataclass() -> None:
    implementation_id = uuid4()
    previous_evidence_id = uuid4()

    dto = CollectImplementationEvidenceInput(
        implementation_id=implementation_id,
        implementation_kind="CORRECTION",
        previous_evidence_id=previous_evidence_id,
        specification_path=Path("spec.md"),
        specification_approval_id="spec-approval-1",
        implementation_plan_path=Path("plan.md"),
        implementation_plan_approval_id="plan-approval-1",
        codex_prompt_path=Path("implementation_prompt.md"),
        codex_prompt="implement this",
        implementation_branch="developer",
        base_commit="abc123",
        implementation_result=None,
        approved_scope=None,
    )

    assert isinstance(dto.implementation_id, UUID)
    assert dto.implementation_kind == "CORRECTION"
    assert dto.previous_evidence_id == previous_evidence_id

    with pytest.raises(FrozenInstanceError):
        dto.base_commit = "changed"


def test_collect_implementation_evidence_output_is_frozen_dataclass() -> None:
    evidence_id = uuid4()
    implementation_id = uuid4()

    dto = CollectImplementationEvidenceOutput(
        success=True,
        evidence_id=evidence_id,
        implementation_id=implementation_id,
        implementation_evidence=None,
        evidence_path=Path("evidence/implementation.json"),
        git_diff_path=Path("evidence/implementation.diff"),
        status="PARTIAL",
        missing_evidence=("git_diff",),
        inconsistencies=(),
        human_approval_required=(),
        error_message=None,
    )

    assert isinstance(dto.evidence_id, UUID)
    assert dto.status == "PARTIAL"

    with pytest.raises(FrozenInstanceError):
        dto.success = False


def test_collect_implementation_evidence_input_preserves_codex_prompt_path() -> None:
    from pathlib import Path
    from uuid import uuid4

    from application.dto import CollectImplementationEvidenceInput

    prompt_path = Path(
        "projects/specflow/prompts/implementation_prompt.md"
    )

    dto = CollectImplementationEvidenceInput(
        implementation_id=uuid4(),
        implementation_kind="INITIAL",
        previous_evidence_id=None,
        specification_path=Path("specification.md"),
        specification_approval_id="spec-approval-001",
        implementation_plan_path=Path("implementation_plan.md"),
        implementation_plan_approval_id="plan-approval-001",
        codex_prompt_path=prompt_path,
        codex_prompt="Implement approved scope.",
        implementation_branch="developer",
        base_commit="abc123",
        implementation_result=None,
        approved_scope=None,
    )

    assert dto.codex_prompt_path == prompt_path
    assert dto.codex_prompt == "Implement approved scope."


def test_collect_implementation_evidence_input_preserves_approved_scope() -> None:
    from application.implementation_evidence import EvidenceScope

    approved_scope = EvidenceScope(
        target_paths=("application/",),
        allowed_changes=("application/*.py",),
        forbidden_changes=("core/",),
    )

    dto = CollectImplementationEvidenceInput(
        implementation_id=uuid4(),
        implementation_kind="INITIAL",
        previous_evidence_id=None,
        specification_path=Path("specification.md"),
        specification_approval_id="spec-approval-001",
        implementation_plan_path=Path("implementation_plan.md"),
        implementation_plan_approval_id="plan-approval-001",
        codex_prompt_path=Path("codex_prompt.md"),
        codex_prompt="Implement approved scope.",
        implementation_branch="developer",
        base_commit="abc123",
        implementation_result=None,
        approved_scope=approved_scope,
    )

    assert dto.approved_scope == approved_scope


def test_collect_implementation_evidence_output_allows_unavailable_artifacts_on_failure() -> None:
    from typing import get_type_hints

    hints = get_type_hints(CollectImplementationEvidenceOutput)

    assert hints["implementation_evidence"] == ImplementationEvidence | None
    assert hints["evidence_path"] == Path | None
    assert hints["git_diff_path"] == Path | None
    assert hints["status"] == str | None


def test_collect_implementation_evidence_output_preserves_failure_without_fake_artifacts() -> None:
    evidence_id = uuid4()
    implementation_id = uuid4()

    output = CollectImplementationEvidenceOutput(
        success=False,
        evidence_id=evidence_id,
        implementation_id=implementation_id,
        implementation_evidence=None,
        evidence_path=None,
        git_diff_path=None,
        status=None,
        missing_evidence=(),
        inconsistencies=(),
        human_approval_required=(),
        error_message="evidence persistence failed",
    )

    assert output.success is False
    assert output.evidence_id == evidence_id
    assert output.implementation_id == implementation_id
    assert output.implementation_evidence is None
    assert output.evidence_path is None
    assert output.git_diff_path is None
    assert output.status is None
    assert output.error_message == "evidence persistence failed"
