from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
from uuid import uuid4

from application.git_merge_service import GitMergeService
from application.current_state_repository import load_current_state
from application.state_transition import transition_state
from application.prepare_review_handoff import PrepareReviewHandoffUseCase
from application.repository_state_provider import RepositoryState
from application.review_handoff import ReviewHandoffOutput, HandoffType


@dataclass(frozen=True)
class FinalApprovalEntryInput:
    handoff: ReviewHandoffOutput
    state_file: Path
    history_dir: Path


@dataclass(frozen=True)
class EntryFailure:
    code: str
    detail: str


@dataclass(frozen=True)
class FinalApprovalEntryOutput:
    request: FinalApprovalEntryInput
    entered: bool = False
    repository_state: RepositoryState | None = None
    head_commit: str | None = None
    failures: tuple[EntryFailure, ...] = ()
    transition: dict | None = None


class FinalApprovalEntryUseCase:
    def __init__(self, git: GitMergeService) -> None:
        self._git = git

    def execute(self, request: FinalApprovalEntryInput) -> FinalApprovalEntryOutput:
        failures = []
        def fail(code, detail):
            failures.append(EntryFailure(code, detail))

        handoff = request.handoff
        try:
            if (handoff.handoff_type != HandoffType.PHASE_6 or handoff.failures
                    or handoff.unresolved_issues or handoff.required_human_action):
                fail('HANDOFF_NOT_READY', 'A PHASE_6 handoff without pending issues is required.')
            # Reuse the existing read-only handoff validation, never rerun or
            # reclassify semantic Review. The original handoff remains intact.
            checked = PrepareReviewHandoffUseCase().execute(handoff.request)
            if checked.handoff_type != HandoffType.PHASE_6 or checked.failures:
                fail('UPSTREAM_NOT_READY', repr(checked.failures or checked.unresolved_issues or checked.reason))
            review = handoff.request.continuation.request.review
            inp = review.review.prepared.review_input
            required = ('evidence', 'saved_diff', 'repository_state', 'specification',
                        'implementation_plan', 'codex_prompt', 'test_state')
            if inp is None:
                fail('REVIEW_INPUT_MISSING', 'Established Review Input is required.')
            else:
                for name in required:
                    if getattr(inp, name) is None:
                        fail('REQUIRED_INFORMATION_MISSING', name)
            identity = inp.evidence.identity if inp and inp.evidence else None
            if identity is None:
                fail('SAVED_IDENTITY_MISSING', 'Saved implementation identity is required.')
            else:
                for name in ('base_branch', 'base_commit', 'implementation_branch'):
                    value = getattr(identity, name)
                    if not isinstance(value, str) or not value.strip():
                        fail('SAVED_IDENTITY_MISSING', name)
                if not identity.implementation_id or not identity.evidence_id:
                    fail('SAVED_IDENTITY_MISSING', 'Implementation and Evidence IDs are required.')
            if handoff.current_state != 'reviewing':
                fail('STATE_MISMATCH', 'The handoff must identify reviewing.')
        except (AttributeError, TypeError, ValueError, KeyError, IndexError) as exc:
            fail('INVALID_INPUT', f'{type(exc).__name__}: {exc}')
        if failures:
            return FinalApprovalEntryOutput(request, failures=tuple(failures))

        observed = None
        head = None
        try:
            observed = self._git.get_state(identity.base_commit)
            if not isinstance(observed, RepositoryState):
                fail('REPOSITORY_ACQUISITION_FAILED', 'Repository state unavailable.')
                observed = None
            elif observed.unavailable_evidence:
                fail('REPOSITORY_INFORMATION_MISSING', repr(observed.unavailable_evidence))
            else:
                if observed.branch != identity.implementation_branch:
                    fail('BRANCH_MISMATCH', f'Saved: {identity.implementation_branch}; observed: {observed.branch}')
                if observed.base_commit != identity.base_commit:
                    fail('BASE_COMMIT_MISMATCH', f'Saved: {identity.base_commit}; observed: {observed.base_commit}')
                # Compare with the reviewed observation, not the Evidence copy:
                # Phase 5 may have explicitly resolved a retained Evidence mismatch.
                if observed.git_diff != inp.repository_state.git_diff:
                    fail('REVIEWED_REPOSITORY_MISMATCH', 'Current Git Diff differs from the reviewed observation.')
        except Exception as exc:
            fail('REPOSITORY_ACQUISITION_FAILED', f'{type(exc).__name__}: {exc}')
        try:
            head = self._git.get_current_head()
            if not isinstance(head, str) or not head.strip():
                head = None
                fail('HEAD_ACQUISITION_FAILED', 'Current HEAD is unavailable.')
        except Exception as exc:
            fail('HEAD_ACQUISITION_FAILED', f'{type(exc).__name__}: {exc}')
        if failures:
            return FinalApprovalEntryOutput(request, repository_state=observed, head_commit=head, failures=tuple(failures))
        try:
            state = load_current_state(request.state_file)
            if state.get('status') != 'reviewing':
                fail('STATE_MISMATCH', 'Persisted State must be reviewing.')
        except (OSError, ValueError, AttributeError) as exc:
            fail('STATE_READ_FAILED', f'{type(exc).__name__}: {exc}')
        if failures:
            return FinalApprovalEntryOutput(request, repository_state=observed, head_commit=head, failures=tuple(failures))
        transition = dict(transition_id=str(uuid4()), from_state='reviewing', to_state='final_approval_pending',
            occurred_at=datetime.now().astimezone().isoformat(),
            reason=f'Final Approval entry validated for implementation {identity.implementation_id}; HEAD {head}')
        try:
            transition_state(request.state_file, request.history_dir, transition)
        except Exception as exc:
            # The existing persistence sequence can have saved State already.
            # Retain the attempted transition; do not claim success or roll back.
            fail('STATE_HISTORY_PERSISTENCE_FAILED', f'{type(exc).__name__}: {exc}')
        return FinalApprovalEntryOutput(request, entered=not failures, repository_state=observed,
            head_commit=head, failures=tuple(failures), transition=transition)
