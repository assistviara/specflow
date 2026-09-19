from pathlib import Path
from typing import Protocol
from uuid import UUID

from application.implementation_evidence import ImplementationEvidence
from application.implementation_evidence_repository import (
    ImplementationEvidenceRepository,
)


def test_implementation_evidence_repository_is_protocol() -> None:
    assert issubclass(
        ImplementationEvidenceRepository,
        Protocol,
    )


def test_repository_contract_exposes_required_operations() -> None:
    annotations = ImplementationEvidenceRepository.__dict__

    assert "save" in annotations
    assert "load" in annotations
    assert "exists" in annotations
    assert "save_diff" in annotations


def test_repository_contract_has_no_update_operation() -> None:
    assert not hasattr(
        ImplementationEvidenceRepository,
        "update",
    )
