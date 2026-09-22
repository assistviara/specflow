from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from application.execution_state_provider import TestState
from application.implementation_evidence import ImplementationEvidence
from application.repository_state_provider import RepositoryState


@dataclass(frozen=True)
class PrepareReviewInputInput:
    implementation_id: UUID
    evidence_id: UUID
    repository_path: Path
    source_paths: tuple[Path, ...]
    test_paths: tuple[Path, ...]
    collection_missing_evidence: tuple[str, ...] = ()
    collection_inconsistencies: tuple[str, ...] = ()
    collection_human_approval_required: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReviewText:
    path: Path
    content: str
    sha256: str


@dataclass(frozen=True)
class ReviewMismatch:
    field: str
    expected: object
    actual: object


@dataclass(frozen=True)
class ReviewInput:
    request: PrepareReviewInputInput
    evidence: ImplementationEvidence | None = None
    specification: ReviewText | None = None
    implementation_plan: ReviewText | None = None
    codex_prompt: ReviewText | None = None
    saved_diff: ReviewText | None = None
    sources: tuple[ReviewText, ...] = ()
    tests: tuple[ReviewText, ...] = ()
    repository_state: RepositoryState | None = None
    test_state: TestState | None = None
    approval_records: tuple[dict, ...] = ()


@dataclass(frozen=True)
class PrepareReviewInputOutput:
    review_input: ReviewInput | None
    acquired: ReviewInput
    missing_information: tuple[str, ...]
    acquisition_errors: tuple[str, ...]
    mismatches: tuple[ReviewMismatch, ...]
