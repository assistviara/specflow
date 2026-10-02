"""Human direct Reminder services for T8; no Candidate storage or execution ports.

The caller supplies the Human-selected Project, kind and optional Workflow.
An omitted Workflow stays unlinked; context never supplies implicit defaults.
Provenance describes origin, not priority, Approval, or a Resume instruction.
"""
from dataclasses import dataclass
from uuid import UUID, uuid4

from human_control.models import Reminder
from human_control.sqlite_repository import HumanControlRepository


@dataclass(frozen=True)
class ReminderResult:
    success: bool
    reminder: Reminder | None = None
    reminders: tuple[Reminder, ...] = ()
    diagnostics: tuple[str, ...] = ()


class ReminderService:
    def __init__(self, repository: HumanControlRepository):
        self.repository = repository

    @staticmethod
    def _stop(exc):
        return ReminderResult(False, diagnostics=(f'{type(exc).__name__}: {exc}',))

    def register(self, project_id: UUID, text: str, kind: str, *,
                 human_confirmed: bool, workflow_id: UUID | None = None,
                 location: str | None = None) -> ReminderResult:
        try:
            if human_confirmed is not True:
                raise ValueError('Explicit Human direct registration required')
            reminder = Reminder(uuid4(), project_id, workflow_id, text, kind, location, 'human_direct')
            self.repository.add_reminder(reminder)
            return ReminderResult(True, reminder=reminder)
        except Exception as exc:
            return self._stop(exc)

    def get(self, project_id: UUID, reminder_id: UUID) -> ReminderResult:
        try:
            return ReminderResult(True, reminder=self.repository.get_reminder(project_id, reminder_id))
        except Exception as exc:
            return self._stop(exc)

    def list_for_project(self, project_id: UUID) -> ReminderResult:
        try:
            return ReminderResult(True, reminders=self.repository.list_reminders(project_id))
        except Exception as exc:
            return self._stop(exc)

    def unlink_workflow(self, project_id: UUID, reminder_id: UUID, *,
                        human_confirmed: bool) -> ReminderResult:
        try:
            if human_confirmed is not True:
                raise ValueError('Explicit Human Workflow unlink decision required')
            return ReminderResult(True,
                reminder=self.repository.unlink_reminder_workflow(project_id, reminder_id))
        except Exception as exc:
            return self._stop(exc)
