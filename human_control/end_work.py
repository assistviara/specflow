"""T6 Human session services; no execution ports or formal Artifact writes.

The synchronous caller invokes end only after its operation has returned control.
This precondition is not an interrupt mechanism or a concurrent-operation monitor.
Service success describes management IO, never formal Workflow completion: callers
must also display projection diagnostics when formal reconstruction cannot succeed.
Focus and deletion are separate explicit Human actions, not effects of End Work.
"""
from dataclasses import dataclass
from uuid import UUID

from human_control.projects import ProjectService
from human_control.resume import PastHumanIntent, ResumeProjection, ResumeService
from human_control.sqlite_repository import HumanControlRepository


@dataclass(frozen=True)
class EndWorkResult:
    success: bool
    projection: ResumeProjection | None = None
    diagnostics: tuple[str, ...] = ()
    intent_saved: bool = False


class EndWorkService:
    def __init__(self, repository: HumanControlRepository, resume: ResumeService):
        if resume.workflows.repository.path != repository.path:
            raise ValueError('Resume and Intent must use the same Human Control database')
        self.repository = repository
        self.projection_service = resume
        self.projects = ProjectService(repository)

    @staticmethod
    def _stop(exc, *, intent_saved=False):
        return EndWorkResult(False, diagnostics=(f'{type(exc).__name__}: {exc}',),
                             intent_saved=intent_saved)

    def resume(self, project_id: UUID, workflow_id: UUID, *, observation=None) -> EndWorkResult:
        try:
            text = self.repository.human_intent(project_id, workflow_id)
            intent = PastHumanIntent(project_id, workflow_id, text) if text is not None else None
            projection = self.projection_service.project(project_id, workflow_id,
                observation=observation, past_intent=intent)
            return EndWorkResult(True, projection, projection.diagnostics)
        except Exception as exc:
            return self._stop(exc)

    def end(self, project_id: UUID, workflow_id: UUID, *, operation_returned: bool,
            intent: str = '', observation=None) -> EndWorkResult:
        saved = False
        try:
            if operation_returned is not True:
                raise ValueError('End Work requires control returned after the synchronous operation')
            self.repository.save_human_intent(project_id, workflow_id, intent)
            saved = bool(intent.strip())
            result = self.resume(project_id, workflow_id, observation=observation)
            return EndWorkResult(result.success, result.projection, result.diagnostics, saved)
        except Exception as exc:
            return self._stop(exc, intent_saved=saved)

    def delete_intent(self, project_id: UUID, workflow_id: UUID, *,
                      human_confirmed: bool) -> EndWorkResult:
        try:
            if human_confirmed is not True:
                raise ValueError('Explicit Human Intent deletion required')
            self.repository.delete_human_intent(project_id, workflow_id)
            return EndWorkResult(True)
        except Exception as exc:
            return self._stop(exc)

    def choose_focus(self, project_id: UUID, workflow_id: UUID, *, choice: str,
                     human_confirmed: bool) -> EndWorkResult:
        try:
            if human_confirmed is not True:
                raise ValueError('Explicit Human focus decision required')
            self.repository.human_intent(project_id, workflow_id)  # Validate ownership.
            if choice == 'keep_active':
                active = self.projects.active_project()
                if active is None or active.project_id != project_id:
                    raise ValueError('Keep Active requires an already Active Project; explicitly Activate separately')
            elif choice == 'sleep':
                self.projects.sleep(project_id, human_confirmed=True)
            else:
                raise ValueError('Unknown End Work focus choice')
            return EndWorkResult(True)
        except Exception as exc:
            return self._stop(exc)
