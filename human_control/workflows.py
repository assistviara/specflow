"""Workflow identity / reference binding, never Application State or Approval."""
import hashlib
from pathlib import Path
from uuid import UUID, uuid4

from human_control.models import Workflow
from human_control.projects import ProjectService
from human_control.sqlite_repository import HumanControlRepository


class WorkflowBoundaryError(ValueError):
    pass


def explicit_path(value) -> Path:
    if not isinstance(value, (str, Path)) or not str(value).strip():
        raise WorkflowBoundaryError('One explicit artifact path is required; no candidate selection.')
    path = Path(value)
    if not path.is_absolute() or any(c in str(path) for c in '*?'):
        raise WorkflowBoundaryError('An absolute, non-pattern artifact reference is required.')
    return path.resolve()


def _overlap(left: Path, right: Path) -> bool:
    return (left == right or left in right.parents or right in left.parents
            or (left.exists() and right.exists() and left.samefile(right)))


# These are explicitly selected read inputs, not per-Workflow output stores.
_SHARED = frozenset(('specification', 'constitution', 'principles', 'decisions',
    'plan_template', 'plan_prompt_template', 'prompt_template', 'revision_template',
    'repository', 'implementation_target'))


class WorkflowService:
    def __init__(self, repository: HumanControlRepository):
        self.repository = repository

    @staticmethod
    def _paths(work, refs):
        reserved = dict(specification=work.specification_path, state=work.state_path,
                        history=work.history_path)
        if set(reserved) & set(refs):
            raise WorkflowBoundaryError('Reserved origin references cannot be shadowed.')
        return {role: explicit_path(path) for role, path in {**reserved, **refs}.items()}

    def _isolation(self, work, refs):
        paths = self._paths(work, refs)
        if _overlap(paths['state'], paths['history']):
            raise WorkflowBoundaryError('State and History references overlap.')
        for role, path in paths.items():
            if role not in _SHARED:
                for shared in _SHARED - {'repository', 'implementation_target'}:
                    if shared in paths and _overlap(path, paths[shared]):
                        raise WorkflowBoundaryError('Writable storage overlaps a formal input.')
        roots = ('state', 'history', 'plan', 'codex_prompt', 'review_dir', 'final_dir')
        for index, role in enumerate(roots):
            for other_role in roots[index + 1:]:
                if role in paths and other_role in paths and _overlap(paths[role], paths[other_role]):
                    raise WorkflowBoundaryError(f'Output references overlap: {role} / {other_role}')
        for other in self.repository.all_workflows():
            if other.workflow_id == work.workflow_id:
                continue
            other_paths = self._paths(other, self.repository.artifact_references(other.workflow_id))
            for role, path in paths.items():
                for other_role, other_path in other_paths.items():
                    # Repository/target roots may enclose formal inputs and outputs.
                    if role in ('repository', 'implementation_target') or other_role in ('repository', 'implementation_target'):
                        continue
                    if role in _SHARED and other_role in _SHARED:
                        continue
                    if _overlap(path, other_path):
                        raise WorkflowBoundaryError(
                            f'Cross-workflow artifact reference: {role} / {other.workflow_id}:{other_role}')
        return paths

    def register(self, project_id: UUID, name: str, specification_path: Path,
                 specification_hash: str, approval_id: str, state_path: Path,
                 history_path: Path, references: dict[str, Path], *, human_confirmed: bool) -> Workflow:
        if human_confirmed is not True:
            raise WorkflowBoundaryError('Explicit Human selection of a new Workflow is required.')
        self.repository.get_project(project_id)
        if not ProjectService(self.repository).workflow_start_gate(project_id).allowed:
            raise WorkflowBoundaryError('Project Constitution confirmation is incomplete.')
        work = Workflow(uuid4(), project_id, name, str(explicit_path(specification_path)),
            specification_hash, approval_id, str(explicit_path(state_path)), str(explicit_path(history_path)))
        refs = {role: str(explicit_path(path)) for role, path in references.items()}
        self._isolation(work, refs)
        self.repository.register_workflow(work, refs)
        return work

    def binding(self, project_id: UUID, workflow_id: UUID):
        work = self.repository.get_workflow(workflow_id)
        if work.project_id != project_id:
            raise WorkflowBoundaryError('Project / Workflow ownership mismatch.')
        self.repository.get_project(project_id)
        refs = self.repository.artifact_references(workflow_id)
        paths = self._isolation(work, refs)
        if not paths['specification'].is_file():
            raise WorkflowBoundaryError('Specification is missing or is not a unique file.')
        # Index association only. Approval validity is exclusively Phase 7's check.
        if hashlib.sha256(paths['specification'].read_bytes()).hexdigest() != work.specification_hash.lower():
            raise WorkflowBoundaryError('Specification content differs from its indexed hash.')
        return work, paths

    def record_references(self, project_id, workflow_id, references):
        work, _ = self.binding(project_id, workflow_id)
        refs = self.repository.artifact_references(workflow_id)
        added = {role: str(explicit_path(path)) for role, path in references.items()}
        self._isolation(work, {**refs, **added})
        self.repository.set_artifact_references(workflow_id, added)
