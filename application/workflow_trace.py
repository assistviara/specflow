"""Read-only projection of Phase 7 workflow results, never an execution gate.

Callers retain each result (including failed attempts and revised generations).
References are paths into detached result snapshots, not new artifact identities.
No approval, correction, retry or completion decision is made here.
"""
from dataclasses import asdict, dataclass
from itertools import groupby
from datetime import datetime
from pathlib import Path

from application.current_state_repository import load_current_state
from application.workflow_entry import WorkflowEntryOutput
from application.plan_workflow import PlanWorkflowOutput
from application.implementation_workflow import ImplementationWorkflowOutput
from application.evidence_workflow import EvidenceWorkflowOutput
from application.review_workflow import ReviewWorkflowOutput
from application.final_approval_workflow import FinalApprovalWorkflowOutput
from application.final_approval_workflow_snapshot import load_checkpoint
from application.implementation_evidence_serializer import implementation_evidence_from_dict
from infrastructure.json_merge_retry_repository import JsonMergeRetryRepository
import json


_STAGES = {
    WorkflowEntryOutput: 'entry', PlanWorkflowOutput: 'plan',
    ImplementationWorkflowOutput: 'implementation', EvidenceWorkflowOutput: 'evidence',
    ReviewWorkflowOutput: 'review', FinalApprovalWorkflowOutput: 'final_approval',
}


@dataclass(frozen=True)
class WorkflowTraceInput:
    state_file: Path
    history_dir: Path
    outputs: tuple


@dataclass(frozen=True)
class TraceReference:
    source: str
    value: object


@dataclass(frozen=True)
class HistoryObservation:
    path: Path
    record: dict | None
    error: str | None = None


@dataclass(frozen=True)
class TransitionObservation:
    source: str
    transition: dict
    history_status: str  # saved / not_saved / unknown / inconsistent


@dataclass(frozen=True)
class StageObservation:
    stage: str
    workflow_success: bool
    snapshot: dict


@dataclass(frozen=True)
class StopObservation:
    stage: str
    reason: object
    actual_state: dict | None
    affected_scope: object = None
    required_human_action: object = None
    restart_point: object = None
    artifact_references: tuple[TraceReference, ...] = ()
    # None means unavailable, never a policy inferred from an exception string.


@dataclass(frozen=True)
class WorkflowTraceOutput:
    success: bool
    workflow_success: bool
    completed: bool
    current_state: dict | None
    state_status: str  # saved (readable) / unknown
    history: tuple[HistoryObservation, ...]
    transitions: tuple[TransitionObservation, ...]
    stages: tuple[StageObservation, ...]
    references: tuple[TraceReference, ...]
    stops: tuple[StopObservation, ...]
    waiting: tuple[str, ...]
    diagnostics: tuple[str, ...]


def _walk(value, path):
    """Index existing DTO fields while retaining their source and generation."""
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _walk(child, f'{path}.{key}')
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            yield from _walk(child, f'{path}.{index}')


def _reference(path):
    key = path.rsplit('.', 1)[-1]
    return (key.endswith(('_id', '_hash', '_path', '_reference', '_references', '_commit'))
            or key in ('identity', 'repository', 'repository_path', 'artifact_paths',
                       'history_path', 'correction_count', 'retry_count', 'handoff',
                       'report', 'classification', 'verification', 'operation',
                       'approval_record', 'head_commit', 'state_file', 'history_dir'))


class WorkflowTraceUseCase:
    """Observe supplied existing results and their State/History; performs no writes."""

    def execute(self, request: WorkflowTraceInput) -> WorkflowTraceOutput:
        diagnostics, stages, refs, stops, transitions = [], [], [], [], []
        checked_paths = set()
        try:
            state = load_current_state(request.state_file)
            if not isinstance(state, dict) or not isinstance(state.get('status'), str):
                raise ValueError('State must contain a status')
        except Exception as exc:
            state = None
            diagnostics.append(f'STATE_UNAVAILABLE: {type(exc).__name__}: {exc}')

        history, records = [], {}
        history_readable = True
        try:
            if not request.history_dir.is_dir():
                raise FileNotFoundError(request.history_dir)
            paths = sorted(request.history_dir.glob('*.json'))
        except OSError as exc:
            paths, history_readable = [], False
            diagnostics.append(f'HISTORY_UNAVAILABLE: {exc}')
        for path in paths:
            record = None
            try:
                record = json.loads(path.read_text(encoding='utf-8'))
                if not isinstance(record, dict) or any(not isinstance(record.get(k), str) or not record[k]
                        for k in ('transition_id', 'from_state', 'to_state', 'occurred_at', 'reason')):
                    raise ValueError('Incomplete transition record')
                timestamp = datetime.fromisoformat(record['occurred_at'])
                if timestamp.tzinfo is None:
                    raise ValueError('Transition timestamp requires timezone')
                if path.stem != record['transition_id'] or record['transition_id'] in records:
                    raise ValueError('Transition identity mismatch')
                records[record['transition_id']] = record
                history.append(HistoryObservation(path, record))
            except (OSError, ValueError, TypeError) as exc:
                history_readable = False
                history.append(HistoryObservation(path, record, str(exc)))
                diagnostics.append(f'HISTORY_UNREADABLE: {path}: {exc}')
        ordered = []
        current = 'specification_ready'
        chronological = sorted(records.values(), key=lambda r: datetime.fromisoformat(r['occurred_at']))
        for _, group in groupby(chronological, key=lambda r: datetime.fromisoformat(r['occurred_at'])):
            pending = list(group)
            # Windows timestamps may tie. Only a unique from/to connection
            # establishes order; never use random UUID filenames as chronology.
            while pending:
                candidates = [r for r in pending if r['from_state'] == current]
                if len(candidates) != 1:
                    diagnostics.append('HISTORY_ORDER_UNAVAILABLE')
                    ordered.extend(pending)
                    current = pending[-1]['to_state']
                    break
                record = candidates[0]
                ordered.append(record)
                pending.remove(record)
                current = record['to_state']
        if not ordered:
            diagnostics.append('HISTORY_MISSING')
        else:
            if ordered[0]['from_state'] != 'specification_ready':
                diagnostics.append('HISTORY_START_MISSING')
            for previous, following in zip(ordered, ordered[1:]):
                if previous['to_state'] != following['from_state']:
                    diagnostics.append('HISTORY_CHAIN_MISMATCH')
            if state is not None and ordered[-1]['to_state'] != state['status']:
                diagnostics.append('STATE_HISTORY_MISMATCH')
        positions = {r['transition_id']: i for i, r in enumerate(ordered)}
        history.sort(key=lambda h: (h.error is not None,
            positions[h.record['transition_id']] if h.error is None else 0))

        if not request.outputs:
            diagnostics.append('WORKFLOW_OUTPUT_MISSING')
        for index, output in enumerate(request.outputs):
            stage = _STAGES.get(type(output))
            if stage is None:
                diagnostics.append(f'UNSUPPORTED_WORKFLOW_OUTPUT: {index}')
                continue
            snapshot = asdict(output)
            ok = (output.can_generate_plan and not output.failures if stage == 'entry'
                  else output.success and not output.stop_reason)
            stages.append(StageObservation(stage, bool(ok), snapshot))
            self._link(output, request.outputs[:index], diagnostics)
            self._saved_output(output, snapshot, diagnostics)
            root = f'outputs.{index}'
            stage_refs = []
            for source, value in _walk(snapshot, root):
                if value is not None and _reference(source):
                    stage_refs.append(TraceReference(source, value))
                key = source.rsplit('.', 1)[-1]
                # Only concrete saved-artifact contracts, not template paths,
                # repository directories or textual object-graph references.
                saved_paths = (value if key == 'artifact_paths' and isinstance(value, (list, tuple)) else
                    (value,) if key in ('evidence_path', 'history_path', 'snapshot_path',
                        'diagnostic_path', 'retry_snapshot_path', 'artifact_path',
                        'implementation_evidence_reference', 'git_diff_reference', 'review_report_reference')
                    and isinstance(value, (str, Path)) and value else ())
                for saved_path in saved_paths:
                    path = Path(saved_path)
                    if path not in checked_paths:
                        checked_paths.add(path)
                        try:
                            content = path.read_bytes()
                            if path.suffix == '.json':
                                json.loads(content)
                        except (OSError, ValueError) as exc:
                            diagnostics.append(f'ARTIFACT_UNAVAILABLE: {source}: {path}: {exc}')
                if key in ('state_file', 'history_dir', 'state_history_dir') and value is not None:
                    expected = request.state_file if key == 'state_file' else request.history_dir
                    if Path(value).resolve() != expected.resolve():
                        diagnostics.append(f'WORKFLOW_STORAGE_MISMATCH: {source}')
                if isinstance(value, dict) and 'transition_id' in value:
                    saved = records.get(value['transition_id'])
                    status = ('saved' if saved == value else 'inconsistent' if saved is not None
                              else 'not_saved' if history_readable else 'unknown')
                    transitions.append(TransitionObservation(source, value, status))
                    if status != 'saved':
                        diagnostics.append(f'TRANSITION_{status.upper()}: {source}')
            refs.extend(stage_refs)
            plan_waiting = (stage == 'plan' and ok and output.draft_result is not None
                            and output.current_state and output.current_state.get('status') == 'plan_approval_pending')
            human_return = (stage == 'final_approval' and output.routing is not None
                            and output.routing.routed and not output.routing.request.decision.is_final_approval)
            if not ok or getattr(output, 'waiting_for_human', False) or plan_waiting or human_return:
                reason = snapshot.get('stop_reason') or snapshot.get('failures') or None
                handoff = snapshot.get('handoff') or {}
                if reason is None:
                    reason = handoff.get('reason')
                action = handoff.get('required_human_action') or None
                scope, restart = None, None
                critical = (handoff.get('request') or {}).get('critical_change')
                if critical and critical.get('impact_reference'):
                    scope = TraceReference(f'{root}.handoff.request.critical_change.impact_reference',
                                           critical['impact_reference'])
                if stage == 'final_approval':
                    if human_return:
                        restart = (output.routing.destination
                                   if output.routing.destination != 'cancelled' else None)
                        if reason is None:
                            reason = output.routing.request.reason
                    for nested in (output.completion, output.merge):
                        if nested is not None and nested.required_human_action:
                            action = nested.required_human_action
                stops.append(StopObservation(stage, reason, state,
                    scope, action, restart, tuple(stage_refs)))

        latest = request.outputs[-1] if request.outputs else None
        if latest is not None and type(latest) in _STAGES:
            observed = latest.current_state
            if observed != state:
                diagnostics.append('LATEST_OUTPUT_STATE_MISMATCH')
        waiting = self._waiting(latest, diagnostics)
        workflow_success = bool(stages) and len(stages) == len(request.outputs) and stages[-1].workflow_success
        # Failed attempts remain visible; they are not changed by a later successful retry.
        completed = type(latest) is FinalApprovalWorkflowOutput and latest.completed
        if state is not None and state['status'] == 'completed' and not completed:
            diagnostics.append('COMPLETION_NOT_ESTABLISHED')
        if completed and (not workflow_success or state is None or state['status'] != 'completed'):
            diagnostics.append('COMPLETION_STATE_MISMATCH')
        return WorkflowTraceOutput(not diagnostics and workflow_success, workflow_success,
            bool(completed), state, 'saved' if state is not None else 'unknown', tuple(history),
            tuple(transitions), tuple(stages), tuple(refs), tuple(stops), waiting, tuple(diagnostics))

    @staticmethod
    def _saved_output(output, snapshot, diagnostics):
        """Compare recorded facts only; never re-run an approval or safety gate."""
        try:
            if type(output) is EvidenceWorkflowOutput and output.collection and output.collection.evidence_path:
                saved = implementation_evidence_from_dict(json.loads(
                    output.collection.evidence_path.read_text(encoding='utf-8')))
                if saved != output.collection.implementation_evidence:
                    raise ValueError('Saved Evidence differs from collected Evidence')
            if type(output) is ReviewWorkflowOutput and output.artifact_paths:
                expected = dict(snapshot, artifact_paths=output.artifact_paths[:-1])
                if json.loads(output.artifact_paths[-1].read_text(encoding='utf-8')) != json.loads(json.dumps(expected, default=str)):
                    raise ValueError('Saved Review snapshot differs from supplied result')
            if type(output) is FinalApprovalWorkflowOutput:
                if output.snapshot_path and output.target:
                    expected = output.ready if output.snapshot_path == output.retry_snapshot_path else output.target
                    if load_checkpoint(output.snapshot_path) != expected:
                        raise ValueError('Saved Final Approval checkpoint differs from supplied result')
                if output.diagnostic_path:
                    if json.loads(output.diagnostic_path.read_text(encoding='utf-8')) != json.loads(json.dumps(snapshot, default=str)):
                        raise ValueError('Saved Final Approval result differs from supplied result')
        except Exception as exc:
            diagnostics.append(f'SAVED_OUTPUT_MISMATCH: {_STAGES[type(output)]}: {type(exc).__name__}: {exc}')

    @staticmethod
    def _link(output, previous, diagnostics):
        # Match existing upstream objects, never decide whether an approval or
        # review SHOULD have succeeded. Historical failed attempts may coexist
        # with a later successful attempt of the same stage.
        expected, kind = None, None
        if type(output) is PlanWorkflowOutput:
            expected, kind = output.entry, WorkflowEntryOutput
        elif type(output) in (ImplementationWorkflowOutput, EvidenceWorkflowOutput, ReviewWorkflowOutput):
            expected = output.request.upstream
            kind = {ImplementationWorkflowOutput: PlanWorkflowOutput,
                    EvidenceWorkflowOutput: ImplementationWorkflowOutput,
                    ReviewWorkflowOutput: EvidenceWorkflowOutput}[type(output)]
        elif type(output) is FinalApprovalWorkflowOutput:
            reviews = [p for p in previous if type(p) is ReviewWorkflowOutput]
            if not reviews:
                diagnostics.append('UPSTREAM_MISSING: review')
            elif output.target is not None:
                received = output.target.request.entry.request.handoff
                if not any(p.success and not p.stop_reason and p.handoff == received
                           and p.ready_for_final_approval for p in reviews):
                    diagnostics.append('UPSTREAM_MISMATCH: review')
            return
        if kind is not None:
            matches = [p for p in previous if type(p) is kind and p == expected]
            if not matches:
                diagnostics.append(f'UPSTREAM_MISSING_OR_MISMATCH: {_STAGES[kind]}')
            elif not (expected.can_generate_plan and not expected.failures if kind is WorkflowEntryOutput
                      else expected.success and not expected.stop_reason):
                diagnostics.append(f'UPSTREAM_FAILED: {_STAGES[kind]}')

    @staticmethod
    def _waiting(output, diagnostics):
        if type(output) is PlanWorkflowOutput:
            if output.success and output.current_state and output.current_state.get('status') == 'plan_approval_pending' and output.draft_result:
                return ('PLAN_APPROVAL',)
        if type(output) is ImplementationWorkflowOutput:
            if output.execution and output.execution.critical_change_required:
                return ('CRITICAL_CHANGE',)
        if type(output) is ReviewWorkflowOutput and output.handoff and output.waiting_for_human:
            return ({'HUMAN_REVIEW': 'REVIEW_HUMAN_HANDOFF',
                     'CRITICAL_CHANGE_APPROVAL': 'CRITICAL_CHANGE'}[output.handoff.handoff_type],)
        if type(output) is FinalApprovalWorkflowOutput:
            if output.waiting_for_human and output.success and output.target:
                return ('FINAL_APPROVAL',)
            if output.merge and not output.success and output.retry_snapshot_path:
                try:
                    journal = JsonMergeRetryRepository(output.retry_snapshot_path.parent / 'retry_history')
                    operation_id = output.merge.operation_id
                    initial = journal.read(operation_id, 'initial')
                    authorization = journal.read(operation_id, 'authorization')
                    attempt = journal.read(operation_id, 'attempt')
                    if (initial and initial.get('operation_id') == operation_id
                            and initial.get('slot') == 'available' and authorization is None and attempt is None):
                        return ('MERGE_RETRY_AUTHORIZATION',)
                except (OSError, ValueError, TypeError) as exc:
                    diagnostics.append(f'RETRY_HISTORY_UNAVAILABLE: {exc}')
        return ()
