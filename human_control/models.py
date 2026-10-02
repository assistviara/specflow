"""Management identities and references, not formal workflow authority."""
from dataclasses import dataclass
from uuid import UUID

CONSTITUTION_FIELDS = ('purpose', 'values', 'rules')
REMINDER_KINDS = ('不具合', '改善案', '新機能候補', '将来構想', '要検討')
REMINDER_PROVENANCES = ('human_direct', 'ai_proposed_human_saved')


@dataclass(frozen=True)
class ConstitutionItem:
    value: str | None
    confirmed: bool


@dataclass(frozen=True)
class WorkflowStartGate:
    unconfirmed: tuple[str, ...]

    @property
    def allowed(self) -> bool:
        return not self.unconfirmed


def require_uuid(value: UUID) -> str:
    if not isinstance(value, UUID):
        raise TypeError('Identity must be a UUID')
    return str(value)


def require_text(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Non-empty text is required')
    return value


@dataclass(frozen=True)
class Project:
    project_id: UUID
    name: str

    def __post_init__(self):
        require_uuid(self.project_id)
        require_text(self.name)


@dataclass(frozen=True)
class Reminder:
    """Human management context, never execution or Approval authority."""
    reminder_id: UUID
    project_id: UUID
    workflow_id: UUID | None
    text: str
    kind: str
    location: str | None
    provenance: str

    def __post_init__(self):
        require_uuid(self.reminder_id)
        require_uuid(self.project_id)
        if self.workflow_id is not None:
            require_uuid(self.workflow_id)
        require_text(self.text)
        if self.kind not in REMINDER_KINDS:
            raise ValueError('One explicit Human-selected Reminder kind is required')
        if self.location is not None and not isinstance(self.location, str):
            raise TypeError('Reminder location must be text or None')
        if self.provenance not in REMINDER_PROVENANCES:
            raise ValueError('Unknown Reminder provenance')


@dataclass(frozen=True)
class Workflow:
    workflow_id: UUID
    project_id: UUID
    name: str
    specification_path: str
    specification_hash: str
    approval_id: str
    state_path: str
    history_path: str

    def __post_init__(self):
        require_uuid(self.workflow_id)
        require_uuid(self.project_id)
        for value in (self.name, self.specification_path, self.approval_id,
                      self.state_path, self.history_path):
            require_text(value)
        # Shape validation only; Application Layer verifies actual artifact bytes.
        if (not isinstance(self.specification_hash, str)
                or len(self.specification_hash) != 64
                or any(c not in '0123456789abcdefABCDEF' for c in self.specification_hash)):
            raise ValueError('Specification hash must be a SHA-256 hex string')
