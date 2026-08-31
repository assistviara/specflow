import hashlib
from pathlib import Path


def validate_approval(
    approval_record: dict | None,
    current_artifact_path: str,
    current_artifact_type: str,
) -> bool:
    if approval_record is None:
        return False

    if approval_record["decision"] != "approved":
        return False

    if approval_record["artifact_type"] != current_artifact_type:
        return False

    if approval_record["artifact_path"] != current_artifact_path:
        return False

    artifact_file = Path(current_artifact_path)

    try:
        current_hash = hashlib.sha256(
            artifact_file.read_bytes()
        ).hexdigest()
    except OSError:
        return False

    if approval_record["artifact_hash"] != current_hash:
        return False

    return True