"""Process-local web boundaries. No execution ports or persistent checkpoints."""
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
import secrets
from threading import Lock
from uuid import UUID

from flask import request, session

from human_control.application_adapter import WorkflowObservation
from human_control.sqlite_repository import HumanControlRepository


class BoundaryError(ValueError):
    pass


def parse_uuid(value):
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        try:
            identity = UUID(value)
            if str(identity) == value.lower():
                return identity
        except ValueError:
            pass
    raise BoundaryError('有効なUUIDが必要です。Project名はidentityではありません。')


@dataclass(frozen=True)
class DatabaseFailure:
    path: str
    reason: str


class FormTokens:
    """One-use, session-bound forms; revision must come from fresh server reads.

    Acceptance is NOT ownership, Artifact validation or Human Approval. Callers
    must revalidate through the service before execution. Never accept a posted
    revision/hash as the current revision. GET cannot consume a token.
    """
    def __init__(self):
        self._pending = {}
        self._lock = Lock()

    @staticmethod
    def _target(action, project_id, workflow_id, revision):
        if not isinstance(action, str) or not action or not isinstance(revision, str) or not revision:
            raise BoundaryError('操作と現在の対象revisionが必要です。')
        return (action, parse_uuid(project_id),
                parse_uuid(workflow_id) if workflow_id is not None else None, revision)

    def issue(self, action, project_id, workflow_id=None, *, revision):
        target = self._target(action, project_id, workflow_id, revision)
        if '_hc_session' not in session:
            session['_hc_session'] = secrets.token_urlsafe(32)
        token = secrets.token_urlsafe(32)
        with self._lock:
            # A newly rendered form invalidates the prior form for this action/target.
            for previous, context in tuple(self._pending.items()):
                if context[:4] == (session['_hc_session'], *target[:3]):
                    del self._pending[previous]
            self._pending[token] = (session['_hc_session'], *target)
        return token

    def consume(self, token, action, project_id, workflow_id=None, *, revision):
        if request.method != 'POST':
            raise BoundaryError('form tokenはPOSTでのみ使用できます。')
        expected = (session.get('_hc_session'), *self._target(action, project_id, workflow_id, revision))
        with self._lock:
            if not isinstance(token, str) or self._pending.get(token) != expected:
                raise BoundaryError('無効・期限切れ・再送または対象不一致のformです。再表示してください。')
            del self._pending[token]


class OutputHolder:
    """Detached actual observations only, never execution authority or recovery."""
    def __init__(self):
        self._outputs = {}

    def put(self, observation):
        if not isinstance(observation, WorkflowObservation):
            raise BoundaryError('実際のWorkflowObservationが必要です。')
        project = parse_uuid(observation.project_id)
        workflow = parse_uuid(observation.workflow_id)
        previous = self._outputs.get(workflow)
        if previous is not None and previous.project_id != project:
            raise BoundaryError('Project / Workflow ownership mismatch')
        self._outputs[workflow] = deepcopy(observation)

    def get(self, project_id, workflow_id):
        project, workflow = parse_uuid(project_id), parse_uuid(workflow_id)
        observation = self._outputs.get(workflow)
        if observation is not None and observation.project_id != project:
            raise BoundaryError('Project / Workflow ownership mismatch')
        return deepcopy(observation)

    def clear(self, workflow_id):
        self._outputs.pop(parse_uuid(workflow_id), None)


class Runtime:
    def __init__(self, path=None):
        self.forms = FormTokens()
        self.outputs = OutputHolder()
        self.failure = None
        self._repository = None
        self.path = str(Path(path).resolve()) if path else '未設定'
        if not path:
            self.failure = DatabaseFailure(self.path, 'DB pathを明示してください。')
            return
        try:
            self._repository = HumanControlRepository(Path(self.path))
        except ValueError:
            self.failure = DatabaseFailure(self.path, '対応するHuman Control DBではありません（application_idまたはschema version）。')
        except Exception:
            # Arbitrary exception text may contain credentials or private inputs.
            self.failure = DatabaseFailure(self.path, 'DBを開けません。存在・アクセス権・ロック・DB形式を確認してください。')

    def require_repository(self):
        if self.failure is not None:
            raise BoundaryError(self.failure.reason)
        return self._repository

    def target(self, project_id, workflow_id=None):
        repo = self.require_repository()
        project = parse_uuid(project_id)
        workflow = parse_uuid(workflow_id) if workflow_id is not None else None
        try:
            repo.get_project(project)
            if workflow is not None and repo.get_workflow(workflow).project_id != project:
                raise BoundaryError('Project / Workflow ownership mismatch')
        except KeyError as exc:
            raise BoundaryError('対象が存在しません。') from exc
        # Later services must still revalidate ownership and formal Artifacts.
        return project, workflow
