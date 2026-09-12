from dataclasses import FrozenInstanceError
from pathlib import Path
from uuid import UUID, uuid4

import pytest

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
    )

    assert dto.codex_prompt_path == prompt_path
    assert dto.codex_prompt == "Implement approved scope."
