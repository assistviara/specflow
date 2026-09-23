import hashlib
from collections.abc import Callable
from pathlib import Path
from uuid import UUID

from application.execution_state_provider import TestStateProvider
from application.implementation_evidence_repository import ImplementationEvidenceRepository
from application.repository_state_provider import RepositoryStateProvider
from application.review_input import (
    PrepareReviewInputInput, PrepareReviewInputOutput, ReviewInput,
    ReviewMismatch, ReviewText,
)
from core.approval_record_repository import ApprovalRecordRepository
from core.approval_validation import validate_approval_result


def _read_text(path: Path) -> ReviewText:
    data = path.read_bytes()
    content = data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return ReviewText(path, content, hashlib.sha256(data).hexdigest())


def _read_selected(root: Path, reference: Path) -> ReviewText:
    root = root.resolve()
    path = (root / reference).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Selected code reference must be inside the repository.")
    return _read_text(path)


class PrepareReviewInputUseCase:
    def __init__(
        self, *, evidence_repository: ImplementationEvidenceRepository,
        approval_repository: ApprovalRecordRepository,
        repository_state_provider: RepositoryStateProvider,
        test_state_provider_factory: Callable[[Path, UUID], TestStateProvider],
    ) -> None:
        self._evidence_repository = evidence_repository
        self._approval_repository = approval_repository
        self._repository_state_provider = repository_state_provider
        # Bind the existing provider to the saved record and requested identity.
        self._test_state_provider_factory = test_state_provider_factory

    def execute(self, request: PrepareReviewInputInput) -> PrepareReviewInputOutput:
        missing: list[str] = []
        errors: list[str] = []
        mismatches: list[ReviewMismatch] = []

        def acquire(label, operation):
            try:
                value = operation()
                if value is None:
                    missing.append(label)
                return value
            except Exception as exc:
                missing.append(label)
                errors.append(f"{label}: {type(exc).__name__}: {exc}")
                return None

        def compare(field, expected, actual):
            if expected != actual:
                mismatches.append(ReviewMismatch(field, expected, actual))

        evidence = acquire("evidence", lambda: self._evidence_repository.load(request.evidence_id))
        values = {}
        approvals = []
        repository = None
        test_state = None
        if evidence is not None:
            compare("identity.implementation_id", request.implementation_id, evidence.identity.implementation_id)
            compare("identity.evidence_id", request.evidence_id, evidence.identity.evidence_id)
            for field in ("base_branch", "base_commit", "implementation_branch"):
                if not getattr(evidence.identity, field):
                    missing.append(f"identity.{field}")
            for label, path in (
                ("specification", evidence.basis.specification_path),
                ("implementation_plan", evidence.basis.implementation_plan_path),
                ("codex_prompt", evidence.basis.codex_prompt_path),
                ("saved_diff", evidence.changes.git_diff_path),
            ):
                values[label] = acquire(label, lambda p=path: _read_text(p) if p is not None else None)
                if label != "saved_diff":
                    expected_hash = getattr(evidence.basis, label + "_hash")
                    if not expected_hash:
                        missing.append(f"{label}.hash")
                    text = values[label]
                    if text is not None:
                        if not text.content.strip():
                            missing.append(label)
                        actual_hash = (
                            hashlib.sha256(text.content.encode("utf-8")).hexdigest()
                            if label == "codex_prompt" else text.sha256
                        )
                        if expected_hash:
                            compare(f"{label}.hash", expected_hash, actual_hash)
            for label, approval_id in (
                ("specification", evidence.basis.specification_approval_id),
                ("implementation_plan", evidence.basis.implementation_plan_approval_id),
            ):
                record = acquire(f"{label}.approval", lambda key=approval_id: self._approval_repository.get(key))
                if record is not None:
                    approvals.append(record)
                    required_keys = ("approval_id", "artifact_type", "artifact_path", "artifact_hash", "decision")
                    if not isinstance(record, dict) or any(
                        not isinstance(record.get(key), str) or not record[key]
                        for key in required_keys
                    ):
                        missing.append(f"{label}.approval")
                    else:
                        compare(f"{label}.approval.approval_id", approval_id, record["approval_id"])
                        text = values[label]
                        if text is not None:
                            validation = acquire(f"{label}.approval_validation", lambda: validate_approval_result(
                                record, str(text.path), label,
                            ))
                            if validation is not None and not validation.is_valid:
                                compare(f"{label}.approval.validation_errors", (), tuple(validation.validation_errors))
            repository = acquire("repository_state", lambda: self._repository_state_provider.get_state(
                evidence.identity.base_commit,
            ))
            test_state = acquire("test_state", lambda: self._test_state_provider_factory(
                evidence.verification.test_execution_record_path, request.implementation_id,
            ).get_state())
            if repository is not None:
                missing.extend(f"repository.{item}" for item in repository.unavailable_evidence)
            if test_state is not None:
                required = {f"{phase}_test_{part}" for phase in ("initial", "target", "full")
                            for part in ("status", "result")}
                required.update(("errors", "test_commands"))
                missing.extend(f"test.{item}" for item in test_state.unavailable_evidence if item in required)
                for field in (
                    "initial_test_status", "initial_test_result", "target_test_status", "target_test_result",
                    "full_test_status", "full_test_result", "tests_created_or_modified", "test_commands",
                    "warnings", "no_tdd_reason",
                ):
                    if field not in test_state.unavailable_evidence:
                        expected = getattr(evidence.verification, field)
                        actual = getattr(test_state, field)
                        if field == "tests_created_or_modified":
                            if set(expected) == set(actual):
                                continue
                        compare(f"test.{field}", expected, actual)
                # Verification.errors also contains Basis errors (Decision 41).
                # Only independently observed Test errors absent from Evidence are mismatches.
                if "errors" not in test_state.unavailable_evidence:
                    absent = tuple(error for error in test_state.errors if error not in evidence.verification.errors)
                    if absent:
                        compare("test.errors", evidence.verification.errors, test_state.errors)
            if repository is not None:
                for field, expected in (
                    ("branch", evidence.identity.implementation_branch),
                    ("base_commit", evidence.identity.base_commit),
                    ("created_files", evidence.changes.created_files),
                    ("modified_files", evidence.changes.modified_files),
                    ("deleted_files", evidence.changes.deleted_files),
                ):
                    marker = "implementation_branch" if field == "branch" else (
                        "changed_files" if field.endswith("_files") else field
                    )
                    if marker not in repository.unavailable_evidence:
                        actual = getattr(repository, field)
                        if field.endswith("_files") and set(expected) == set(actual):
                            continue
                        compare(f"repository.{field}", expected, actual)
                if values["saved_diff"] is not None and "git_diff" not in repository.unavailable_evidence:
                    compare("repository.git_diff", values["saved_diff"].content, repository.git_diff)
        for label, paths in (("sources", request.source_paths), ("tests", request.test_paths)):
            if not paths:
                missing.append(label)
            texts = []
            for path in dict.fromkeys(paths):
                text = acquire(f"{label}:{path}", lambda p=path: _read_selected(request.repository_path, p))
                if text is not None:
                    texts.append(text)
            values[label] = tuple(texts)
        acquired = ReviewInput(
            request=request, evidence=evidence, repository_state=repository,
            test_state=test_state, approval_records=tuple(approvals), **values,
        )
        return PrepareReviewInputOutput(
            acquired if not missing else None, acquired, tuple(dict.fromkeys(missing)),
            tuple(errors), tuple(mismatches),
        )
