from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from application.implementation_evidence import (
    EvidenceBasis,
    EvidenceChanges,
    EvidenceCodexSummary,
    EvidenceDeviations,
    EvidenceIdentity,
    EvidenceScope,
    EvidenceVerification,
    ImplementationEvidence,
)
from application.implementation_result_parser import ImplementationResult


def implementation_evidence_to_dict(
    evidence: ImplementationEvidence,
) -> dict[str, Any]:
    result = evidence.codex_summary.implementation_result

    return {
        "identity": {
            "evidence_id": str(evidence.identity.evidence_id),
            "implementation_id": str(
                evidence.identity.implementation_id
            ),
            "implementation_kind": (
                evidence.identity.implementation_kind
            ),
            "previous_evidence_id": (
                str(evidence.identity.previous_evidence_id)
                if evidence.identity.previous_evidence_id is not None
                else None
            ),
            "status": evidence.identity.status,
            "created_at": evidence.identity.created_at.isoformat(),
        },
        "basis": {
            "specification_path": evidence.basis.specification_path.as_posix(),
            "specification_hash": evidence.basis.specification_hash,
            "specification_approval_id": (
                evidence.basis.specification_approval_id
            ),
            "implementation_plan_path": evidence.basis.implementation_plan_path.as_posix(),
            "implementation_plan_hash": (
                evidence.basis.implementation_plan_hash
            ),
            "implementation_plan_approval_id": (
                evidence.basis.implementation_plan_approval_id
            ),
            "codex_prompt_path": evidence.basis.codex_prompt_path.as_posix(),
            "codex_prompt_hash": evidence.basis.codex_prompt_hash,
        },
        "scope": (
            {
                "target_paths": list(evidence.scope.target_paths),
                "allowed_changes": list(
                    evidence.scope.allowed_changes
                ),
                "forbidden_changes": list(
                    evidence.scope.forbidden_changes
                ),
            }
            if evidence.scope is not None
            else None
        ),
        "changes": {
            "created_files": list(evidence.changes.created_files),
            "modified_files": list(
                evidence.changes.modified_files
            ),
            "deleted_files": list(evidence.changes.deleted_files),
            "git_diff_path": (
                evidence.changes.git_diff_path.as_posix()
                if evidence.changes.git_diff_path is not None
                else None
            ),
            "change_summary": evidence.changes.change_summary,
        },
        "verification": {
            "commands": list(evidence.verification.commands),
            "tests_created_or_modified": list(
                evidence.verification.tests_created_or_modified
            ),
            "test_commands": list(
                evidence.verification.test_commands
            ),
            "initial_test_status": (
                evidence.verification.initial_test_status
            ),
            "initial_test_result": (
                evidence.verification.initial_test_result
            ),
            "target_test_status": (
                evidence.verification.target_test_status
            ),
            "target_test_result": (
                evidence.verification.target_test_result
            ),
            "full_test_status": (
                evidence.verification.full_test_status
            ),
            "full_test_result": (
                evidence.verification.full_test_result
            ),
            "errors": list(evidence.verification.errors),
            "warnings": list(evidence.verification.warnings),
            "no_tdd_reason": evidence.verification.no_tdd_reason,
        },
        "deviations": {
            "out_of_scope_changes": list(
                evidence.deviations.out_of_scope_changes
            ),
            "unplanned_changes": list(
                evidence.deviations.unplanned_changes
            ),
            "unfinished_items": list(
                evidence.deviations.unfinished_items
            ),
            "human_approval_required": list(
                evidence.deviations.human_approval_required
            ),
        },
        "codex_summary": {
            "implementation_result": {
                "implementation_summary": (
                    result.implementation_summary
                ),
                "changed_files": result.changed_files,
                "executed_commands": result.executed_commands,
                "test_execution_status": (
                    result.test_execution_status
                ),
                "test_result": result.test_result,
                "test_execution_error": (
                    result.test_execution_error
                ),
                "errors": result.errors,
                "warnings": result.warnings,
                "incomplete_items": result.incomplete_items,
                "human_approval_required": (
                    result.human_approval_required
                ),
                "test_required": result.test_required,
                "technical_retry_safe": (
                    result.technical_retry_safe
                ),
                "technical_retry_operation": (
                    result.technical_retry_operation
                ),
            },
        },
    }


def implementation_evidence_from_dict(
    data: dict[str, Any],
) -> ImplementationEvidence:
    identity = data["identity"]
    basis = data["basis"]
    scope = data["scope"]
    changes = data["changes"]
    verification = data["verification"]
    deviations = data["deviations"]
    codex_summary = data["codex_summary"]
    result = codex_summary["implementation_result"]

    return ImplementationEvidence(
        identity=EvidenceIdentity(
            evidence_id=UUID(identity["evidence_id"]),
            implementation_id=UUID(
                identity["implementation_id"]
            ),
            implementation_kind=identity[
                "implementation_kind"
            ],
            previous_evidence_id=(
                UUID(identity["previous_evidence_id"])
                if identity["previous_evidence_id"] is not None
                else None
            ),
            status=identity["status"],
            created_at=datetime.fromisoformat(
                identity["created_at"]
            ),
        ),
        basis=EvidenceBasis(
            specification_path=Path(
                basis["specification_path"]
            ),
            specification_hash=basis[
                "specification_hash"
            ],
            specification_approval_id=basis[
                "specification_approval_id"
            ],
            implementation_plan_path=Path(
                basis["implementation_plan_path"]
            ),
            implementation_plan_hash=basis[
                "implementation_plan_hash"
            ],
            implementation_plan_approval_id=basis[
                "implementation_plan_approval_id"
            ],
            codex_prompt_path=Path(
                basis["codex_prompt_path"]
            ),
            codex_prompt_hash=basis["codex_prompt_hash"],
        ),
        scope=(
            EvidenceScope(
                target_paths=tuple(scope["target_paths"]),
                allowed_changes=tuple(
                    scope["allowed_changes"]
                ),
                forbidden_changes=tuple(
                    scope["forbidden_changes"]
                ),
            )
            if scope is not None
            else None
        ),
        changes=EvidenceChanges(
            created_files=tuple(
                changes["created_files"]
            ),
            modified_files=tuple(
                changes["modified_files"]
            ),
            deleted_files=tuple(
                changes["deleted_files"]
            ),
            git_diff_path=(
                Path(changes["git_diff_path"])
                if changes["git_diff_path"] is not None
                else None
            ),
            change_summary=changes["change_summary"],
        ),
        verification=EvidenceVerification(
            commands=tuple(
                verification["commands"]
            ),
            tests_created_or_modified=tuple(
                verification["tests_created_or_modified"]
            ),
            test_commands=tuple(
                verification["test_commands"]
            ),
            initial_test_status=verification[
                "initial_test_status"
            ],
            initial_test_result=verification[
                "initial_test_result"
            ],
            target_test_status=verification[
                "target_test_status"
            ],
            target_test_result=verification[
                "target_test_result"
            ],
            full_test_status=verification[
                "full_test_status"
            ],
            full_test_result=verification[
                "full_test_result"
            ],
            errors=tuple(verification["errors"]),
            warnings=tuple(verification["warnings"]),
            no_tdd_reason=verification[
                "no_tdd_reason"
            ],
        ),
        deviations=EvidenceDeviations(
            out_of_scope_changes=tuple(
                deviations["out_of_scope_changes"]
            ),
            unplanned_changes=tuple(
                deviations["unplanned_changes"]
            ),
            unfinished_items=tuple(
                deviations["unfinished_items"]
            ),
            human_approval_required=tuple(
                deviations["human_approval_required"]
            ),
        ),
        codex_summary=EvidenceCodexSummary(
            implementation_result=ImplementationResult(
                **result
            ),
        ),
    )
