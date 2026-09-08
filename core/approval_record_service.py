import hashlib
from pathlib import Path

from core.approval_record import build_approval_record


def build_approval_record_from_artifact(
    approval_id: str,
    artifact_type: str,
    artifact_path: str,
    decision: str,
    approved_at: str,
    comment: str,
) -> dict:
    artifact_hash = hashlib.sha256(
        Path(artifact_path).read_bytes()
    ).hexdigest()

    return build_approval_record(
        approval_id=approval_id,
        artifact_type=artifact_type,
        artifact_path=artifact_path,
        artifact_hash=artifact_hash,
        decision=decision,
        approved_at=approved_at,
        comment=comment,
    )
