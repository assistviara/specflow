import hashlib
from pathlib import Path

from dataclasses import dataclass


@dataclass(frozen=True)
class ApprovalValidationResult:
    is_valid: bool
    approval_id: str | None
    artifact_type: str | None
    validation_errors: list[str]
    validation_warnings: list[str]

def validate_approval_result(
    approval_record: dict | None,
    current_artifact_path: str,
    current_artifact_type: str,
) -> ApprovalValidationResult:
    if approval_record is None:
        return ApprovalValidationResult(
            is_valid=False,
            approval_id=None,
            artifact_type=None,
            validation_errors=["approval record not found"],
            validation_warnings=[],
        )

    if approval_record["decision"] != "approved":
        return ApprovalValidationResult(
            is_valid=False,
            approval_id=approval_record.get("approval_id"),
            artifact_type=approval_record["artifact_type"],
            validation_errors=[
                "approval decision is not approved"
            ],
            validation_warnings=[],
        )

    if approval_record["artifact_type"] != current_artifact_type:
        return ApprovalValidationResult(
            is_valid=False,
            approval_id=approval_record.get("approval_id"),
            artifact_type=approval_record["artifact_type"],
            validation_errors=[
                "artifact type does not match"
            ],
            validation_warnings=[],
        )

    if approval_record["artifact_path"] != current_artifact_path:
        return ApprovalValidationResult(
            is_valid=False,
            approval_id=approval_record.get("approval_id"),
            artifact_type=approval_record["artifact_type"],
            validation_errors=[
                "artifact path does not match"
            ],
            validation_warnings=[],
        )

    artifact_file = Path(current_artifact_path)

    try:
        current_hash = hashlib.sha256(
            artifact_file.read_bytes()
        ).hexdigest()
    except OSError:
        return ApprovalValidationResult(
            is_valid=False,
            approval_id=approval_record.get("approval_id"),
            artifact_type=approval_record["artifact_type"],
            validation_errors=[
                "artifact hash could not be calculated"
            ],
            validation_warnings=[],
        )

    if approval_record["artifact_hash"] != current_hash:
        return ApprovalValidationResult(
            is_valid=False,
            approval_id=approval_record.get("approval_id"),
            artifact_type=approval_record["artifact_type"],
            validation_errors=[
                "artifact hash does not match"
            ],
            validation_warnings=[],
        )

    return ApprovalValidationResult(
        is_valid=True,
        approval_id=approval_record.get("approval_id"),
        artifact_type=approval_record["artifact_type"],
        validation_errors=[],
        validation_warnings=[],
    )


def validate_approval(
    approval_record: dict | None,
    current_artifact_path: str,
    current_artifact_type: str,
) -> bool:
    return validate_approval_result(
        approval_record,
        current_artifact_path,
        current_artifact_type,
    ).is_valid