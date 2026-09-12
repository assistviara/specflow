from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from application.implementation_evidence import EvidenceBasis


def test_evidence_basis_is_frozen_dataclass() -> None:
    basis = EvidenceBasis(
        specification_path=Path(
            "projects/specflow/docs/drafts/"
            "application_layer_specification_v0.2.0-draft.md"
        ),
        specification_hash="spec-hash",
        specification_approval_id="spec-approval-1",
        implementation_plan_path=Path(
            "projects/specflow/docs/drafts/"
            "application_layer_implementation_plan_v0.1.0-draft.md"
        ),
        implementation_plan_hash="plan-hash",
        implementation_plan_approval_id="plan-approval-1",
        codex_prompt_path=Path("prompts/codex_implementation_prompt.md"),
        codex_prompt_hash="prompt-hash",
    )

    assert basis.specification_hash == "spec-hash"
    assert basis.implementation_plan_hash == "plan-hash"
    assert basis.codex_prompt_hash == "prompt-hash"

    with pytest.raises(FrozenInstanceError):
        basis.specification_hash = "changed"


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("specification_hash", ""),
        ("specification_approval_id", ""),
        ("implementation_plan_hash", ""),
        ("implementation_plan_approval_id", ""),
        ("codex_prompt_hash", ""),
    ],
)
def test_evidence_basis_rejects_empty_required_strings(
    field_name: str,
    field_value: str,
) -> None:
    values = {
        "specification_path": Path("spec.md"),
        "specification_hash": "spec-hash",
        "specification_approval_id": "spec-approval-1",
        "implementation_plan_path": Path("plan.md"),
        "implementation_plan_hash": "plan-hash",
        "implementation_plan_approval_id": "plan-approval-1",
        "codex_prompt_path": Path("prompt.md"),
        "codex_prompt_hash": "prompt-hash",
    }

    values[field_name] = field_value

    with pytest.raises(ValueError):
        EvidenceBasis(**values)


def test_evidence_basis_allows_unavailable_hashes_as_none() -> None:
    from pathlib import Path

    from application.implementation_evidence import EvidenceBasis

    basis = EvidenceBasis(
        specification_path=Path("specification.md"),
        specification_hash=None,
        specification_approval_id="spec-approval-001",
        implementation_plan_path=Path("implementation_plan.md"),
        implementation_plan_hash=None,
        implementation_plan_approval_id="plan-approval-001",
        codex_prompt_path=Path("codex_prompt.md"),
        codex_prompt_hash=None,
    )

    assert basis.specification_hash is None
    assert basis.implementation_plan_hash is None
    assert basis.codex_prompt_hash is None
