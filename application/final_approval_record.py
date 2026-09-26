"""Persist explicit Final Approval and validate it against the saved Target."""
from dataclasses import dataclass

from application.final_approval_decision import (
    FinalApprovalDecisionOutput, FinalApprovalDecisionUseCase,
)
from application.final_approval_target import load_final_approval_target
from core.approval_record_repository import ApprovalRecordRepository
from core.approval_record_service import build_approval_record_from_artifact
from core.approval_validation import ApprovalValidationResult, validate_approval_result


@dataclass(frozen=True)
class FinalApprovalRecordInput:
    decision: FinalApprovalDecisionOutput
    approval_id: str
    approved_at: str
    comment: str


@dataclass(frozen=True)
class RecordFailure:
    code: str
    detail: str


@dataclass(frozen=True)
class FinalApprovalRecordOutput:
    request: FinalApprovalRecordInput
    approval_record: dict | None = None
    # Means save returned normally, not that validation succeeded.
    saved: bool = False
    approval_validation_result: ApprovalValidationResult | None = None
    failures: tuple[RecordFailure, ...] = ()

    @property
    def approval_valid(self) -> bool:
        """Artifact validation only; not permission to merge or transition."""
        return (self.saved and not self.failures
                and self.approval_validation_result is not None
                and self.approval_validation_result.is_valid)


class FinalApprovalRecordUseCase:
    def __init__(self, approval_repository: ApprovalRecordRepository) -> None:
        self._approval_repository = approval_repository

    def execute(self, request: FinalApprovalRecordInput) -> FinalApprovalRecordOutput:
        try:
            decision = request.decision
            if (not isinstance(decision, FinalApprovalDecisionOutput)
                    or not decision.is_final_approval
                    or FinalApprovalDecisionUseCase().execute(decision.request) != decision):
                raise ValueError('An explicit Final Approval received by Target 3 is required')
            target = decision.request.target
            path = target.request.artifact_path
            if load_final_approval_target(path) != target.artifact:
                raise ValueError('Saved Target differs from the Target presented to Human')
            record = build_approval_record_from_artifact(
                approval_id=request.approval_id,
                artifact_type='final_approval_target',
                artifact_path=str(path),
                decision='approved',
                approved_at=request.approved_at,
                comment=request.comment,
            )
            # Do not bind an old Human decision to bytes changed since Target 2.
            if record['artifact_hash'] != target.artifact_hash:
                raise ValueError('Target bytes differ from the Target presented to Human')
        except (OSError, ValueError, TypeError, AttributeError, KeyError) as exc:
            return FinalApprovalRecordOutput(request, failures=(RecordFailure(
                'APPROVAL_INPUT_INVALID', f'{type(exc).__name__}: {exc}'),))

        try:
            self._approval_repository.save(record)
        except Exception as exc:
            # A failed save may have written data. Never claim success or retry.
            return FinalApprovalRecordOutput(request, record, failures=(RecordFailure(
                'APPROVAL_SAVE_FAILED', f'{type(exc).__name__}: {exc}'),))
        try:
            saved_record = self._approval_repository.get(request.approval_id)
        except Exception as exc:
            return FinalApprovalRecordOutput(request, record, saved=True, failures=(RecordFailure(
                'APPROVAL_READ_FAILED', f'{type(exc).__name__}: {exc}'),))
        try:
            validation = validate_approval_result(saved_record, str(path), 'final_approval_target')
            failures = []
            if saved_record != record:
                failures.append(RecordFailure('SAVED_RECORD_MISMATCH',
                    'Reloaded Approval Record differs from the explicit Human approval record'))
            if not validation.is_valid:
                failures.append(RecordFailure('APPROVAL_VALIDATION_FAILED',
                    '; '.join(validation.validation_errors)))
        except Exception as exc:
            return FinalApprovalRecordOutput(request, saved_record, saved=True, failures=(RecordFailure(
                'APPROVAL_VALIDATION_FAILED', f'{type(exc).__name__}: {exc}'),))
        return FinalApprovalRecordOutput(request, saved_record, True, validation, tuple(failures))
