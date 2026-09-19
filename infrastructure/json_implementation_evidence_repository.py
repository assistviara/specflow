import json
from pathlib import Path
from uuid import UUID

from application.implementation_evidence import (
    ImplementationEvidence,
)
from application.implementation_evidence_serializer import (
    implementation_evidence_from_dict,
    implementation_evidence_to_dict,
)


class JsonImplementationEvidenceRepository:
    def __init__(
        self,
        evidence_dir: Path,
    ) -> None:
        self._evidence_dir = evidence_dir

    def save(
        self,
        evidence: ImplementationEvidence,
    ) -> Path:
        self._evidence_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        path = self._json_path(
            evidence.identity.evidence_id
        )

        if path.exists():
            raise FileExistsError(path)

        data = implementation_evidence_to_dict(
            evidence
        )

        path.write_text(
            json.dumps(
                data,
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        return path

    def load(
        self,
        evidence_id: UUID,
    ) -> ImplementationEvidence:
        path = self._json_path(evidence_id)

        if not path.exists():
            raise FileNotFoundError(path)

        data = json.loads(
            path.read_text(encoding="utf-8")
        )

        return implementation_evidence_from_dict(
            data
        )

    def exists(
        self,
        evidence_id: UUID,
    ) -> bool:
        return self._json_path(
            evidence_id
        ).exists()

    def save_diff(
        self,
        evidence_id: UUID,
        diff: str,
    ) -> Path:
        self._evidence_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        path = self._diff_path(evidence_id)

        if path.exists():
            raise FileExistsError(path)

        path.write_text(
            diff,
            encoding="utf-8",
        )

        return path

    def _json_path(
        self,
        evidence_id: UUID,
    ) -> Path:
        return (
            self._evidence_dir
            / f"implementation_{evidence_id}.json"
        )

    def _diff_path(
        self,
        evidence_id: UUID,
    ) -> Path:
        return (
            self._evidence_dir
            / f"implementation_{evidence_id}.diff"
        )
