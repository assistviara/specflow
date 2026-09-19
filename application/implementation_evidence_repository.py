from pathlib import Path
from typing import Protocol
from uuid import UUID

from application.implementation_evidence import ImplementationEvidence


class ImplementationEvidenceRepository(Protocol):
    def save(
        self,
        evidence: ImplementationEvidence,
    ) -> Path:
        ...

    def load(
        self,
        evidence_id: UUID,
    ) -> ImplementationEvidence:
        ...

    def exists(
        self,
        evidence_id: UUID,
    ) -> bool:
        ...

    def save_diff(
        self,
        evidence_id: UUID,
        diff: str,
    ) -> Path:
        ...
