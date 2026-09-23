"""Freeze the existing Review and entry information; never create an Approval."""
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path

from application.final_approval_entry import FinalApprovalEntryOutput
from application.current_state_repository import load_current_state
from application.implementation_evidence_serializer import implementation_evidence_from_dict


@dataclass(frozen=True)
class FinalApprovalTargetArtifact:
    implementation_branch: str
    head_commit: str
    base_commit: str
    implementation_evidence_reference: str
    git_diff_reference: str
    review_report_reference: str

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f'{name} is required')


@dataclass(frozen=True)
class FinalApprovalTargetInput:
    entry: FinalApprovalEntryOutput
    artifact_path: Path
    implementation_evidence_reference: Path
    git_diff_reference: Path
    review_report_reference: Path


@dataclass(frozen=True)
class TargetFailure:
    code: str
    detail: str


@dataclass(frozen=True)
class FinalApprovalTargetOutput:
    request: FinalApprovalTargetInput
    artifact: FinalApprovalTargetArtifact | None = None
    artifact_hash: str | None = None
    failures: tuple[TargetFailure, ...] = ()
    saved_paths: tuple[Path, ...] = ()

    @property
    def succeeded(self) -> bool:
        return self.artifact is not None and self.artifact_hash is not None and not self.failures


def artifact_hash(path: Path) -> str:
    """Same file-byte SHA-256 contract as the existing Approval Record service."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_final_approval_target(path: Path) -> FinalApprovalTargetArtifact:
    return FinalApprovalTargetArtifact(**json.loads(path.read_text(encoding='utf-8')))


def _json_bytes(data: dict) -> bytes:
    return (json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')


def _save_json(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(content)


class FinalApprovalTargetUseCase:
    def execute(self, request: FinalApprovalTargetInput) -> FinalApprovalTargetOutput:
        try:
            if not request.entry.entered or request.entry.failures:
                raise ValueError('Successful Target 1 Entry is required')
            paths = (request.artifact_path, request.implementation_evidence_reference,
                     request.git_diff_reference, request.review_report_reference)
            for name, path in zip(('artifact_path', 'implementation_evidence_reference',
                                   'git_diff_reference', 'review_report_reference'), paths):
                if not isinstance(path, Path) or path == Path('.'):
                    raise ValueError(f'{name} is required')
            if len({path.resolve() for path in paths}) != len(paths):
                raise ValueError('Target and reference paths must be distinct')
            if request.artifact_path.exists():
                raise ValueError('Target Artifact already exists; snapshots cannot be overwritten')
            if load_current_state(request.entry.request.state_file).get('status') != 'final_approval_pending':
                raise ValueError('Current State must be final_approval_pending')
            review = request.entry.request.handoff.request.continuation.request.review
            inp = review.review.prepared.review_input
            identity = inp.evidence.identity
            artifact = FinalApprovalTargetArtifact(identity.implementation_branch, request.entry.head_commit,
                identity.base_commit, str(request.implementation_evidence_reference),
                str(request.git_diff_reference), str(request.review_report_reference))
            if review.report is None:
                raise ValueError('Existing Review Report is required')
            # Verify supplied references identify the acquired artifacts, without
            # rerunning Entry or Review and without normalizing Evidence.
            saved_evidence = implementation_evidence_from_dict(json.loads(
                request.implementation_evidence_reference.read_text(encoding='utf-8')))
            if saved_evidence != inp.evidence:
                raise ValueError('Evidence reference does not identify the Entry Evidence')
            if request.git_diff_reference.read_text(encoding='utf-8') != request.entry.repository_state.git_diff:
                raise ValueError('Git Diff reference does not identify the Entry Git Diff')
            report_bytes = _json_bytes(asdict(review.report))
            target_bytes = _json_bytes(asdict(artifact))
            report_exists = request.review_report_reference.exists()
            if report_exists and request.review_report_reference.read_bytes() != report_bytes:
                raise ValueError('Existing Review Report snapshot differs; it cannot be overwritten')
        except (OSError, ValueError, TypeError, AttributeError, KeyError) as exc:
            return FinalApprovalTargetOutput(request, failures=(TargetFailure('TARGET_INPUT_INVALID',
                f'{type(exc).__name__}: {exc}'),))

        saved = []
        try:
            if not report_exists:
                _save_json(request.review_report_reference, report_bytes)
                saved.append(request.review_report_reference)
            _save_json(request.artifact_path, target_bytes)
            saved.append(request.artifact_path)
            if (request.review_report_reference.read_bytes() != report_bytes
                    or request.artifact_path.read_bytes() != target_bytes):
                raise ValueError('Saved snapshot bytes differ from the prepared content')
            digest = artifact_hash(request.artifact_path)
        except (OSError, ValueError) as exc:
            # Preserve completed saves for diagnosis; never overwrite or delete
            # existing artifacts to hide a partial persistence failure.
            return FinalApprovalTargetOutput(request, failures=(TargetFailure('TARGET_PERSISTENCE_FAILED',
                f'{type(exc).__name__}: {exc}'),), saved_paths=tuple(saved))
        return FinalApprovalTargetOutput(request, artifact, digest, saved_paths=tuple(saved))
