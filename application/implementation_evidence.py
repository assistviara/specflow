from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import UUID

from application.implementation_result_parser import ImplementationResult


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
class EvidenceBasis:
    specification_path: Path
    specification_hash: str
    specification_approval_id: str
    implementation_plan_path: Path
    implementation_plan_hash: str
    implementation_plan_approval_id: str
    codex_prompt_path: Path
    codex_prompt_hash: str

    def __post_init__(self) -> None:
        required_strings = {
            "specification_hash": self.specification_hash,
            "specification_approval_id": self.specification_approval_id,
            "implementation_plan_hash": self.implementation_plan_hash,
            "implementation_plan_approval_id": (
                self.implementation_plan_approval_id
            ),
            "codex_prompt_hash": self.codex_prompt_hash,
        }

        for field_name, value in required_strings.items():
            if not value.strip():
                raise ValueError(
                    f"{field_name} must not be empty"
                )



@dataclass(frozen=True)
class EvidenceScope:
    target_paths: tuple[str, ...]
    allowed_changes: tuple[str, ...]
    forbidden_changes: tuple[str, ...]



@dataclass(frozen=True)
class EvidenceChanges:
    created_files: tuple[str, ...]
    modified_files: tuple[str, ...]
    deleted_files: tuple[str, ...]
    git_diff_path: Path | None
    change_summary: str



@dataclass(frozen=True)
class EvidenceVerification:
    commands: tuple[str, ...]
    tests_created_or_modified: tuple[str, ...]
    test_commands: tuple[str, ...]
    initial_test_status: str
    initial_test_result: str
    target_test_status: str
    target_test_result: str
    full_test_status: str
    full_test_result: str
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    no_tdd_reason: str | None

    def __post_init__(self) -> None:
        valid_statuses = {
            "COMPLETED",
            "ERROR",
            "NOT_RUN",
        }
        valid_results = {
            "PASS",
            "FAIL",
            "NONE",
        }

        statuses = (
            self.initial_test_status,
            self.target_test_status,
            self.full_test_status,
        )
        results = (
            self.initial_test_result,
            self.target_test_result,
            self.full_test_result,
        )

        if any(status not in valid_statuses for status in statuses):
            raise ValueError("invalid test status")

        if any(result not in valid_results for result in results):
            raise ValueError("invalid test result")

        pairs = (
            (self.initial_test_status, self.initial_test_result),
            (self.target_test_status, self.target_test_result),
            (self.full_test_status, self.full_test_result),
        )

        for status, result in pairs:
            if status == "COMPLETED" and result not in {
                "PASS",
                "FAIL",
            }:
                raise ValueError(
                    "COMPLETED test status requires PASS or FAIL"
                )

            if status in {"ERROR", "NOT_RUN"} and result != "NONE":
                raise ValueError(
                    "ERROR or NOT_RUN test status requires NONE"
                )



@dataclass(frozen=True)
class EvidenceDeviations:
    out_of_scope_changes: tuple[str, ...]
    unplanned_changes: tuple[str, ...]
    unfinished_items: tuple[str, ...]
    human_approval_required: tuple[str, ...]



@dataclass(frozen=True)
class EvidenceCodexSummary:
    implementation_result: ImplementationResult


@dataclass(frozen=True)
class ImplementationEvidence:
    identity: EvidenceIdentity
    basis: EvidenceBasis
    scope: EvidenceScope
    changes: EvidenceChanges
    verification: EvidenceVerification
    deviations: EvidenceDeviations
    codex_summary: EvidenceCodexSummary
