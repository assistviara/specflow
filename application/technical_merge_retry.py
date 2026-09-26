"""Human-authorized, once-only retry of a recorded Phase 6 Git failure."""
from dataclasses import asdict, dataclass, replace
from enum import Enum
from datetime import datetime, date
import hashlib
import json
from pathlib import Path
from uuid import UUID, uuid4, uuid5, NAMESPACE_URL

from application.git_merge_service import GitMergeResult, GitMergeVerification, GitMergeService
from core.approval_record_repository import ApprovalRecordRepository
from application.merge_execution import MergeExecutionOutput, MergeExecutionUseCase
from application.merge_preconditions import MergePreconditionsOutput, MergePreconditionsUseCase
from application.repository_state_provider import RepositoryState
from core.merge_retry_repository import MergeRetryRepository


def _plain(value):
    def scalar(item):
        if isinstance(item, (datetime, date)):
            return item.isoformat()
        if isinstance(item, (Path, UUID)):
            return str(item)
        if isinstance(item, Enum):
            return item.value
        raise TypeError(f'Unsupported history value: {type(item).__name__}')
    return json.loads(json.dumps(value, default=scalar, sort_keys=True, allow_nan=False))


def _files(ready):
    target = ready.request.request.decision.request.target
    paths = (target.request.artifact_path, Path(target.artifact.implementation_evidence_reference),
             Path(target.artifact.git_diff_reference), Path(target.artifact.review_report_reference))
    return {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def _result_data(result):
    return _plain(dict(operation=asdict(result.operation) if result.operation else None,
        verification=asdict(result.verification) if result.verification else None,
        failures=result.failures, rechecked=result.rechecked == result.request,
        retry_history=result.retry_history))


def _state(data):
    if data is None:
        return None
    data = dict(data)
    for name in ('created_files', 'modified_files', 'deleted_files', 'unavailable_evidence'):
        data[name] = tuple(data[name])
    return RepositoryState(**data)


def _restore(data, ready):
    operation = verification = None
    if data['operation'] is not None:
        values = dict(data['operation'])
        values['repository_state'] = _state(values['repository_state'])
        for name in ('errors', 'conflicts', 'warnings'):
            values[name] = tuple(values[name])
        operation = GitMergeResult(**values)
    if data['verification'] is not None:
        values = dict(data['verification'])
        values['repository_state'] = _state(values['repository_state'])
        values['errors'] = tuple(values['errors'])
        if values['pending_operations'] is not None:
            values['pending_operations'] = tuple(values['pending_operations'])
        verification = GitMergeVerification(**values)
    return MergeExecutionOutput(ready, ready if data['rechecked'] else None,
        operation, verification, tuple(data['failures']), data.get('retry_history'))


@dataclass(frozen=True)
class MergeRetryAuthorization:
    operation_id: str
    safe_reexecution_confirmed: bool = False
    reason: str = ''


@dataclass(frozen=True)
class MergeRetryOutput:
    operation_id: str
    result: MergeExecutionOutput | None = None
    initial: MergeExecutionOutput | None = None
    retry_count: int | None = None
    failures: tuple[str, ...] = ()

    @property
    def required_human_action(self) -> tuple[str, ...]:
        if self.failures or self.result is None or not self.result.succeeded:
            return ('Inspect the recorded operation and Git facts; no automatic correction or retry.',)
        return ()


class TechnicalMergeRetryUseCase:
    def __init__(self, git: GitMergeService, approvals: ApprovalRecordRepository, history: MergeRetryRepository) -> None:
        self._git, self._approvals, self._history = git, approvals, history

    def start(self, ready: MergePreconditionsOutput) -> MergeRetryOutput:
        operation_id = str(uuid4())
        result = None
        try:
            if not isinstance(ready, MergePreconditionsOutput) or not ready.merge_ready or ready.failures:
                raise ValueError('Initial Target 6 result required; retry results cannot be registered')
            repository = self._git.get_repository_identity()
            if not isinstance(repository, str) or not repository.strip():
                raise ValueError('Repository identity unavailable')
            # One initial execution for this approved operation scope. A retry
            # failure cannot acquire a fresh UUID by re-entering start().
            record = ready.approval_record
            scope = json.dumps([repository, record['approval_id'], record['artifact_path'],
                record['artifact_hash']], ensure_ascii=False)
            registration = str(uuid5(NAMESPACE_URL, scope))
            self._history.create(registration, 'registration', dict(operation_id=operation_id))
            manifest = dict(version=1, operation_id=operation_id, repository=repository,
                context=_plain(asdict(ready)), files=_files(ready))
            self._history.create(operation_id, 'operation', manifest)
            result = MergeExecutionUseCase(self._git, self._approvals).execute(ready)
            kind = None
            if result.rechecked == ready and result.operation is not None and not result.succeeded:
                kind = 'verification' if result.operation.command_success else 'merge'
            self._history.create(operation_id, 'initial', dict(operation_id=operation_id,
                slot='available' if kind else 'closed', kind=kind, result=_result_data(result)))
            return MergeRetryOutput(operation_id, result, result, 0)
        except Exception as exc:
            detail = f'Initial operation/history failure: {type(exc).__name__}: {exc}'
            if result is not None:
                result = replace(result, failures=(*result.failures, detail))
            return MergeRetryOutput(operation_id, result, result, failures=(detail,))

    def authorize(self, operation_id: str, authorization: MergeRetryAuthorization) -> None:
        # This method receives a Human selection, never infers one from failure text.
        if (type(authorization) is not MergeRetryAuthorization
                or authorization.operation_id != operation_id
                or authorization.safe_reexecution_confirmed is not True
                or not isinstance(authorization.reason, str) or not authorization.reason.strip()):
            raise ValueError('Explicit Human safety confirmation for this operation is required')
        manifest, initial = self._load(operation_id)
        if self._history.read(operation_id, 'attempt') is not None:
            raise ValueError('Retry slot already consumed')
        self._history.create(operation_id, 'authorization', asdict(authorization))

    def _load(self, operation_id):
        manifest = self._history.read(operation_id, 'operation')
        initial = self._history.read(operation_id, 'initial')
        if (not manifest or manifest.get('version') != 1 or manifest.get('operation_id') != operation_id
                or not initial or initial.get('operation_id') != operation_id
                or initial.get('slot') != 'available' or initial.get('kind') not in ('merge', 'verification')):
            raise ValueError('Known initial failed operation with an explicitly available slot required')
        return manifest, initial

    def _validate(self, manifest, initial, ready):
        if manifest['context'] != _plain(asdict(ready)) or manifest['files'] != _files(ready):
            raise ValueError('Approved inputs or recorded operation identity changed')
        if self._git.get_repository_identity() != manifest['repository']:
            raise ValueError('Repository identity changed')
        validated = MergePreconditionsUseCase(self._git, self._approvals).validate_approval(ready.request)
        if validated.failures:
            raise ValueError(f'Approval/Artifact preconditions failed: {validated.failures}')
        original = _restore(initial['result'], ready)
        operation = original.operation
        artifact = ready.request.request.decision.request.target.artifact
        if (original.succeeded or operation is None or original.rechecked != ready
                or operation.repository != manifest['repository'] or operation.operation != 'merge'
                or operation.target_branch != 'developer' or operation.source_branch != artifact.implementation_branch
                or operation.approved_commit != artifact.head_commit
                or operation.pre_commit != ready.observed_destination_head):
            raise ValueError('Recorded failed operation identity is inconsistent')
        verification_retry = initial['kind'] == 'verification'
        if verification_retry != operation.command_success:
            raise ValueError('Operation stage mismatch')
        if verification_retry and (operation.errors or operation.conflicts or not operation.post_commit):
            raise ValueError('Successful merge result required for verification-only retry')
        state = self._git.get_state(artifact.base_commit)
        head = self._git.get_current_head()
        source = self._git.get_branch_head(artifact.implementation_branch)
        target = self._git.get_branch_head('developer')
        pending = self._git.get_pending_operations()
        expected_target = operation.post_commit if verification_retry else operation.pre_commit
        if (not isinstance(state, RepositoryState) or state.unavailable_evidence or state.git_status
                or state.base_commit != artifact.base_commit or pending != ()
                or source != artifact.head_commit or target != expected_target):
            raise ValueError('Current Repository Safety or commit identity does not permit retry')
        if state.branch == artifact.implementation_branch and state.git_diff != ready.observed_repository.git_diff:
            raise ValueError('Observed source diff differs from approved diff')
        allowed = ('developer',) if verification_retry else (artifact.implementation_branch, 'developer')
        if state.branch not in allowed or head != (artifact.head_commit if state.branch == artifact.implementation_branch else expected_target):
            raise ValueError('Current branch/HEAD is not valid for this failed operation')
        return original, dict(repository_state=asdict(state), head=head, source=source,
                              target=target, pending_operations=pending)

    def retry(self, operation_id: str, ready: MergePreconditionsOutput) -> MergeRetryOutput:
        original = result = None
        count = None
        try:
            manifest, initial = self._load(operation_id)
            if manifest['context'] != _plain(asdict(ready)):
                raise ValueError('Operation context changed')
            original = _restore(initial['result'], ready)
            prior_attempt = self._history.read(operation_id, 'attempt')
            prior_result = self._history.read(operation_id, 'result')
            if prior_attempt is not None or prior_result is not None:
                count = 1
                if prior_result is not None:
                    result = _restore(prior_result['result'], ready)
                raise ValueError('Retry consumed or execution outcome unknown; never retry again')
            authorization = self._history.read(operation_id, 'authorization')
            if (not authorization or authorization.get('operation_id') != operation_id
                    or authorization.get('safe_reexecution_confirmed') is not True
                    or not isinstance(authorization.get('reason'), str) or not authorization['reason'].strip()):
                raise ValueError('Matching explicit Human authorization required')
            count = 0
            original, observed = self._validate(manifest, initial, ready)
            attempt = dict(operation_id=operation_id, slot='consumed', retry_count=1,
                kind=initial['kind'], authorization=authorization, observed=_plain(observed))
            # The durable exclusive claim precedes every retry Git operation.
            count = None  # A failed/partial claim is unknown, never presumed unused.
            self._history.create(operation_id, 'attempt', attempt)
            count = 1
            operation = original.operation
            verification = None
            history = dict(initial=initial, attempt=attempt)
            try:
                # Check again after recording the claim; a failed recheck cannot release it.
                self._validate(manifest, initial, ready)
                if initial['kind'] == 'merge':
                    operation = self._git.retry_merge(operation)
                if (not isinstance(operation, GitMergeResult) or not operation.command_success
                        or operation.errors or operation.conflicts
                        or operation.repository != original.operation.repository
                        or operation.source_branch != original.operation.source_branch
                        or operation.target_branch != original.operation.target_branch
                        or operation.approved_commit != original.operation.approved_commit
                        or operation.pre_commit != original.operation.pre_commit or operation.operation != 'merge'):
                    raise ValueError('Retried merge failed or changed operation identity')
                artifact = ready.request.request.decision.request.target.artifact
                verification = self._git.verify_merge(operation, base_commit=artifact.base_commit)
                if not isinstance(verification, GitMergeVerification) or not verification.verified:
                    raise ValueError('Post-merge verification failed, including content verification')
                validated = MergePreconditionsUseCase(self._git, self._approvals).validate_approval(ready.request)
                if validated.failures or manifest['files'] != _files(ready) or manifest['context'] != _plain(asdict(ready)):
                    raise ValueError('Approved inputs changed during retry')
                result = MergeExecutionOutput(ready, ready, operation, verification, retry_history=history)
            except Exception as exc:
                result = MergeExecutionOutput(ready, ready, operation, verification,
                    (f'{type(exc).__name__}: {exc}',), history)
            self._history.create(operation_id, 'result', dict(operation_id=operation_id, retry_count=1,
                result=_result_data(result)))
            return MergeRetryOutput(operation_id, result, original, count, result.failures)
        except Exception as exc:
            detail = f'Retry stopped: {type(exc).__name__}: {exc}'
            if result is not None:
                result = replace(result, failures=(*result.failures, detail))
            return MergeRetryOutput(operation_id, result, original, count, (detail,))
