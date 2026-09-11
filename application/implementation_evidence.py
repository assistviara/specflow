from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class EvidenceIdentity:
    evidence_id: UUID
    implementation_id: UUID
    implementation_kind: str
    previous_evidence_id: UUID | None
    status: str
    created_at: datetime

    def __post_init__(self) -> None:
        if self.implementation_kind not in {
            "INITIAL",
            "CORRECTION",
            "REIMPLEMENTATION",
        }:
            raise ValueError("invalid implementation_kind")

        if self.status not in {
            "COLLECTED",
            "PARTIAL",
        }:
            raise ValueError("invalid status")

        if (
            self.implementation_kind == "INITIAL"
            and self.previous_evidence_id is not None
        ):
            raise ValueError(
                "INITIAL evidence must not have previous_evidence_id"
            )

        if (
            self.implementation_kind in {
                "CORRECTION",
                "REIMPLEMENTATION",
            }
            and self.previous_evidence_id is None
        ):
            raise ValueError(
                "CORRECTION or REIMPLEMENTATION evidence "
                "requires previous_evidence_id"
            )

        if (
            self.created_at.tzinfo is None
            or self.created_at.utcoffset() is None
        ):
            raise ValueError(
                "created_at must be timezone-aware"
            )


@dataclass(frozen=True)
class ImplementationEvidence:
    identity: dict[str, Any]
    basis: dict[str, Any]
    scope: dict[str, Any]
    changes: dict[str, Any]
    verification: dict[str, Any]
    deviations: dict[str, Any]
    codex_summary: dict[str, Any]
