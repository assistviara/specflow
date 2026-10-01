"""Human project management; never runs or transitions an Application workflow."""
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from application.current_state_repository import load_current_state
from pathlib import Path
from human_control.models import Project, Workflow, ConstitutionItem, WorkflowStartGate
from human_control.sqlite_repository import HumanControlRepository


@dataclass(frozen=True)
class ConstitutionChange:
    constitution: dict[str, ConstitutionItem]
    workflows: tuple[Workflow, ...]
    reason: str

    @property
    def human_review_required(self) -> bool:
        return bool(self.workflows)


class ProjectService:
    def __init__(self, repository: HumanControlRepository):
        self.repository = repository

    def create(self, name: str) -> Project:
        project = Project(uuid4(), name)
        self.repository.add_project(project)
        return project

    def register_existing(self, name: str, reference: str, *, human_confirmed: bool) -> Project:
        if human_confirmed is not True:
            raise ValueError('Explicit Human registration required')
        project = Project(uuid4(), name)
        self.repository.add_project(project, existing_reference=reference)
        return project

    def constitution(self, project_id: UUID) -> dict[str, ConstitutionItem]:
        return self.repository.constitution(project_id)

    def activate(self, project_id: UUID, *, human_confirmed: bool) -> None:
        if human_confirmed is not True:
            raise ValueError('Explicit Human focus decision required')
        self.repository.activate_project(project_id)

    def sleep(self, project_id: UUID, *, human_confirmed: bool,
              occurred_at: datetime | None = None) -> None:
        if human_confirmed is not True:
            raise ValueError('Explicit Human focus decision required')
        timestamp = occurred_at if occurred_at is not None else datetime.now(timezone.utc)
        if not isinstance(timestamp, datetime) or timestamp.utcoffset() is None:
            raise ValueError('A timezone-aware Sleep action timestamp is required')
        self.repository.sleep_project(project_id, timestamp.astimezone(timezone.utc).isoformat(timespec='microseconds'))

    def active_project(self) -> Project | None:
        return self.repository.active_project()

    def sleeping_projects(self) -> tuple[Project, ...]:
        return self.repository.sleeping_projects()

    def recent_sleeping(self) -> tuple[Project, ...]:
        return self.repository.sleeping_projects(recent=True)

    def workflow_start_gate(self, project_id: UUID) -> WorkflowStartGate:
        # This is only the Constitution gate, never Specification Approval.
        return WorkflowStartGate(tuple(field for field, item in self.constitution(project_id).items()
                                       if not item.confirmed or not item.value or not item.value.strip()))

    def confirm_constitution(self, project_id: UUID, field: str, expected_value: str,
                             *, human_confirmed: bool) -> None:
        self.repository.confirm_constitution(project_id, field, expected_value,
                                             human_confirmed=human_confirmed)

    def update_constitution(self, project_id: UUID, field: str, value: str | None) -> ConstitutionChange:
        changed = self.repository.update_constitution(project_id, field, value)
        affected = []
        if changed:
            for work in self.repository.list_workflows(project_id):
                try:
                    state = load_current_state(Path(work.state_path))
                except (OSError, ValueError):
                    state = None
                # Missing/unknown is not evidence of completion. Retain references for Human inspection.
                if not isinstance(state, dict) or state.get('status') not in ('completed', 'cancelled'):
                    affected.append(work)
        return ConstitutionChange(self.constitution(project_id), tuple(affected),
            'Constitution changed. Inspect the referenced current Workflow and formal artifacts; '
            'Human must decide continuation, stopping or reconsideration. Unknown State is not inferred.'
            if affected else '')
