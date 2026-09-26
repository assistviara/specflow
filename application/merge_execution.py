"""Execute an approved merge and verify it, without completing the workflow."""
from dataclasses import dataclass
from pathlib import Path

from application.git_merge_service import GitMergeService, GitMergeResult, GitMergeVerification
from application.merge_preconditions import MergePreconditionsOutput, MergePreconditionsUseCase
from core.approval_record_repository import ApprovalRecordRepository


@dataclass(frozen=True)
class MergeExecutionOutput:
    request: MergePreconditionsOutput
    rechecked: MergePreconditionsOutput | None = None
    operation: GitMergeResult | None = None
    verification: GitMergeVerification | None = None
    failures: tuple[str, ...] = ()
    retry_history: dict | None = None

    @property
    def succeeded(self) -> bool:
        return (not self.failures and isinstance(self.operation, GitMergeResult)
                and self.operation.command_success and not self.operation.errors
                and not self.operation.conflicts and isinstance(self.verification, GitMergeVerification)
                and self.verification.verified)


class MergeExecutionUseCase:
    def __init__(self, git: GitMergeService, approvals: ApprovalRecordRepository) -> None:
        self._git = git
        self._approvals = approvals

    def execute(self, request: MergePreconditionsOutput) -> MergeExecutionOutput:
        if not isinstance(request, MergePreconditionsOutput) or not request.merge_ready or request.failures:
            return MergeExecutionOutput(request, failures=('Target 6 merge-ready result is required',))
        # Reuse Target 6 rather than duplicating its Approval and safety rules.
        refreshed = MergePreconditionsUseCase(self._git, self._approvals).execute(request.request)
        if not refreshed.merge_ready or refreshed != request:
            return MergeExecutionOutput(request, refreshed, failures=('Merge preconditions changed or failed',))
        target = request.request.request.decision.request.target
        artifact = target.artifact
        try:
            paths = (target.request.artifact_path, Path(artifact.implementation_evidence_reference),
                     Path(artifact.git_diff_reference), Path(artifact.review_report_reference))
            snapshots = {path: path.read_bytes() for path in paths}
        except OSError as exc:
            return MergeExecutionOutput(request, refreshed, failures=(f'Artifact read failed: {exc}',))
        operation = verification = None
        try:
            operation = self._git.merge(artifact.implementation_branch, artifact.head_commit,
                refreshed.observed_destination_head)
            if not isinstance(operation, GitMergeResult):
                raise ValueError('Structured Git merge result unavailable')
            if (operation.source_branch != artifact.implementation_branch
                    or operation.target_branch != 'developer' or operation.operation != 'merge'
                    or operation.approved_commit != artifact.head_commit
                    or operation.pre_commit != refreshed.observed_destination_head):
                raise ValueError('Merge operation does not identify the approved source and target')
            if not operation.command_success or operation.errors or operation.conflicts:
                return MergeExecutionOutput(request, refreshed, operation, failures=('Git merge operation failed',))
            verification = self._git.verify_merge(operation, base_commit=artifact.base_commit)
            if not isinstance(verification, GitMergeVerification) or not verification.verified:
                return MergeExecutionOutput(request, refreshed, operation, verification,
                    ('Post-merge verification failed',))
            if any(path.read_bytes() != content for path, content in snapshots.items()):
                raise ValueError('Approved Artifact or reference changed during merge')
            approval_id = request.request.request.approval.request.approval_id
            if self._approvals.get(approval_id) != refreshed.approval_record:
                raise ValueError('Saved Approval changed during merge')
        except Exception as exc:
            return MergeExecutionOutput(request, refreshed, operation, verification,
                (f'{type(exc).__name__}: {exc}',))
        return MergeExecutionOutput(request, refreshed, operation, verification)
