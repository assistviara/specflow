def build_approval_record(
    approval_id: str,
    artifact_type: str,
    artifact_path: str,
    artifact_hash: str,
    decision: str,
    approved_at: str,
    comment: str,
) -> dict:
    return {
        "approval_id": approval_id,
        "artifact_type": artifact_type,
        "artifact_path": artifact_path,
        "artifact_hash": artifact_hash,
        "decision": decision,
        "approved_at": approved_at,
        "comment": comment,
    }