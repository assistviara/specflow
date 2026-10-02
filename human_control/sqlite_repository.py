"""Small SQLite index. No Artifact IO, approval decisions or State transitions."""
from contextlib import contextmanager
from pathlib import Path
import sqlite3
from uuid import UUID

from human_control.models import Project, Workflow, require_text, require_uuid
from human_control.models import CONSTITUTION_FIELDS, ConstitutionItem


_SCHEMA = (
    '''CREATE TABLE human_intents (
        workflow_id TEXT PRIMARY KEY NOT NULL REFERENCES workflows(workflow_id),
        text TEXT NOT NULL)''',
    '''CREATE TABLE project_focus (
        project_id TEXT PRIMARY KEY NOT NULL REFERENCES projects(project_id),
        is_active INTEGER NOT NULL CHECK(is_active IN (0, 1)),
        last_slept_at TEXT)''',
    'CREATE UNIQUE INDEX one_active_project ON project_focus(is_active) WHERE is_active = 1',
    '''CREATE TABLE constitution (
        project_id TEXT NOT NULL REFERENCES projects(project_id),
        field TEXT NOT NULL CHECK(field IN ('purpose', 'values', 'rules')),
        value TEXT, confirmed INTEGER NOT NULL CHECK(confirmed IN (0, 1)),
        PRIMARY KEY(project_id, field))''',
    '''CREATE TABLE existing_projects (
        project_id TEXT PRIMARY KEY REFERENCES projects(project_id),
        reference TEXT NOT NULL)''',
    'CREATE TABLE projects (project_id TEXT PRIMARY KEY NOT NULL, name TEXT NOT NULL)',
    '''CREATE TABLE workflows (
        workflow_id TEXT PRIMARY KEY NOT NULL,
        project_id TEXT NOT NULL REFERENCES projects(project_id),
        name TEXT NOT NULL, specification_path TEXT NOT NULL,
        specification_hash TEXT NOT NULL, approval_id TEXT NOT NULL,
        state_path TEXT NOT NULL, history_path TEXT NOT NULL)''',
    '''CREATE TABLE artifact_references (
        workflow_id TEXT NOT NULL REFERENCES workflows(workflow_id),
        role TEXT NOT NULL, path TEXT NOT NULL,
        PRIMARY KEY (workflow_id, role))''',
)
_APPLICATION_ID = 0x53463841
_SCHEMA_VERSION = 4


class HumanControlRepository:
    def __init__(self, path: Path):
        self.path = Path(path).resolve()
        # Opening never creates or upgrades a database.
        with self._connection() as db:
            if (db.execute('PRAGMA application_id').fetchone()[0] != _APPLICATION_ID
                    or db.execute('PRAGMA user_version').fetchone()[0] != _SCHEMA_VERSION):
                raise ValueError('Not a supported Human Control database; no migration performed')

    @staticmethod
    def initialize(path: Path) -> None:
        path = Path(path).resolve()
        # Exclusive creation protects existing files, including old JSON/SQLite.
        with path.open('xb'):
            pass
        db = sqlite3.connect(path)
        try:
            with db:
                db.execute('BEGIN')
                for statement in _SCHEMA:
                    db.execute(statement)
                db.execute(f'PRAGMA application_id = {_APPLICATION_ID}')
                db.execute(f'PRAGMA user_version = {_SCHEMA_VERSION}')
        finally:
            db.close()
        # On failure the file is retained; do not silently replace or retry it.

    @contextmanager
    def _connection(self):
        db = sqlite3.connect(self.path.as_uri() + '?mode=rw', uri=True, timeout=0)
        try:
            db.execute('PRAGMA foreign_keys = ON')
            with db:
                yield db
        finally:
            db.close()

    def add_project(self, project: Project, *, existing_reference: str | None = None) -> None:
        with self._connection() as db:
            db.execute('INSERT INTO projects VALUES (?, ?)',
                       (require_uuid(project.project_id), project.name))
            if existing_reference is not None:
                db.execute('INSERT INTO existing_projects VALUES (?, ?)',
                           (str(project.project_id), require_text(existing_reference)))

    @staticmethod
    def _intent_owner(db, project_id: UUID, workflow_id: UUID) -> str:
        project, workflow = require_uuid(project_id), require_uuid(workflow_id)
        row = db.execute('SELECT project_id FROM workflows WHERE workflow_id = ?',
                         (workflow,)).fetchone()
        if row is None or row[0] != project:
            raise ValueError('Project / Workflow ownership mismatch')
        if db.execute('SELECT 1 FROM projects WHERE project_id = ?', (project,)).fetchone() is None:
            raise ValueError('Project is missing')
        return workflow

    def human_intent(self, project_id: UUID, workflow_id: UUID) -> str | None:
        with self._connection() as db:
            workflow = self._intent_owner(db, project_id, workflow_id)
            row = db.execute('SELECT text FROM human_intents WHERE workflow_id = ?',
                             (workflow,)).fetchone()
        return row[0] if row else None

    def save_human_intent(self, project_id: UUID, workflow_id: UUID, text: str) -> None:
        if not isinstance(text, str):
            raise TypeError('Human Intent must be text')
        with self._connection() as db:
            db.execute('BEGIN IMMEDIATE')
            workflow = self._intent_owner(db, project_id, workflow_id)
            if text.strip():
                db.execute('''INSERT INTO human_intents VALUES (?, ?)
                    ON CONFLICT(workflow_id) DO UPDATE SET text = excluded.text''',
                    (workflow, text))

    def delete_human_intent(self, project_id: UUID, workflow_id: UUID) -> None:
        with self._connection() as db:
            db.execute('BEGIN IMMEDIATE')
            workflow = self._intent_owner(db, project_id, workflow_id)
            db.execute('DELETE FROM human_intents WHERE workflow_id = ?', (workflow,))

    def existing_project_reference(self, project_id: UUID) -> str | None:
        self.get_project(project_id)
        with self._connection() as db:
            row = db.execute('SELECT reference FROM existing_projects WHERE project_id = ?',
                             (str(project_id),)).fetchone()
        return row[0] if row else None

    def activate_project(self, project_id: UUID) -> None:
        self.get_project(project_id)
        with self._connection() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('UPDATE project_focus SET is_active = 0 WHERE is_active = 1')
            db.execute('''INSERT INTO project_focus VALUES (?, 1, NULL)
                ON CONFLICT(project_id) DO UPDATE SET is_active = 1''', (str(project_id),))

    def sleep_project(self, project_id: UUID, occurred_at: str) -> None:
        self.get_project(project_id)
        with self._connection() as db:
            db.execute('''INSERT INTO project_focus VALUES (?, 0, ?)
                ON CONFLICT(project_id) DO UPDATE SET is_active = 0, last_slept_at = excluded.last_slept_at''',
                (str(project_id), occurred_at))

    def active_project(self) -> Project | None:
        with self._connection() as db:
            row = db.execute('''SELECT p.project_id, p.name FROM projects p
                JOIN project_focus f ON p.project_id = f.project_id WHERE f.is_active = 1''').fetchone()
        return Project(UUID(row[0]), row[1]) if row else None

    def sleeping_projects(self, *, recent: bool = False) -> tuple[Project, ...]:
        # Absence of an explicit activation never makes a new project Active.
        query = '''SELECT p.project_id, p.name FROM projects p
            LEFT JOIN project_focus f ON p.project_id = f.project_id
            WHERE COALESCE(f.is_active, 0) = 0'''
        query += (' AND f.last_slept_at IS NOT NULL ORDER BY f.last_slept_at DESC, p.project_id LIMIT 3'
                  if recent else ' ORDER BY p.project_id')
        with self._connection() as db:
            rows = db.execute(query).fetchall()
        return tuple(Project(UUID(row[0]), row[1]) for row in rows)

    def constitution(self, project_id: UUID) -> dict[str, ConstitutionItem]:
        self.get_project(project_id)
        with self._connection() as db:
            rows = db.execute('SELECT field, value, confirmed FROM constitution WHERE project_id = ?',
                              (str(project_id),)).fetchall()
        result = {field: ConstitutionItem(None, False) for field in CONSTITUTION_FIELDS}
        result.update({field: ConstitutionItem(value, bool(confirmed)) for field, value, confirmed in rows})
        return result

    def update_constitution(self, project_id: UUID, field: str, value: str | None) -> bool:
        self.get_project(project_id)
        if field not in CONSTITUTION_FIELDS:
            raise ValueError('Unknown Constitution item')
        if value is not None and not isinstance(value, str):
            raise TypeError('Constitution value must be text or None')
        with self._connection() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT value FROM constitution WHERE project_id = ? AND field = ?',
                             (str(project_id), field)).fetchone()
            if (row[0] if row else None) == value:
                return False
            db.execute('''INSERT INTO constitution VALUES (?, ?, ?, 0)
                ON CONFLICT(project_id, field) DO UPDATE SET value = excluded.value, confirmed = 0''',
                (str(project_id), field, value))
        return True

    def confirm_constitution(self, project_id: UUID, field: str, expected_value: str,
                             *, human_confirmed: bool) -> None:
        self.get_project(project_id)
        if human_confirmed is not True or field not in CONSTITUTION_FIELDS:
            raise ValueError('Explicit Human confirmation of a known item required')
        require_text(expected_value)
        with self._connection() as db:
            changed = db.execute('''UPDATE constitution SET confirmed = 1
                WHERE project_id = ? AND field = ? AND value = ?''',
                (str(project_id), field, expected_value))
            if changed.rowcount != 1:
                raise ValueError('Constitution content changed or is missing; reconfirm current content')

    def get_project(self, project_id: UUID) -> Project:
        with self._connection() as db:
            row = db.execute('SELECT project_id, name FROM projects WHERE project_id = ?',
                             (require_uuid(project_id),)).fetchone()
        if row is None:
            raise KeyError(project_id)
        return Project(UUID(row[0]), row[1])

    def rename_project(self, project_id: UUID, name: str) -> None:
        with self._connection() as db:
            changed = db.execute('UPDATE projects SET name = ? WHERE project_id = ?',
                                 (require_text(name), require_uuid(project_id)))
            if changed.rowcount != 1:
                raise KeyError(project_id)

    def add_workflow(self, workflow: Workflow) -> None:
        with self._connection() as db:
            db.execute('INSERT INTO workflows VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (
                require_uuid(workflow.workflow_id), require_uuid(workflow.project_id),
                workflow.name, workflow.specification_path, workflow.specification_hash,
                workflow.approval_id, workflow.state_path, workflow.history_path))

    @staticmethod
    def _workflow(row) -> Workflow:
        return Workflow(UUID(row[0]), UUID(row[1]), *row[2:])

    def get_workflow(self, workflow_id: UUID) -> Workflow:
        with self._connection() as db:
            row = db.execute('SELECT * FROM workflows WHERE workflow_id = ?',
                             (require_uuid(workflow_id),)).fetchone()
        if row is None:
            raise KeyError(workflow_id)
        return self._workflow(row)

    def list_workflows(self, project_id: UUID) -> tuple[Workflow, ...]:
        with self._connection() as db:
            rows = db.execute('SELECT * FROM workflows WHERE project_id = ? ORDER BY workflow_id',
                              (require_uuid(project_id),)).fetchall()
        return tuple(self._workflow(row) for row in rows)

    def all_workflows(self) -> tuple[Workflow, ...]:
        """Read identities across Projects to detect shared output references."""
        with self._connection() as db:
            rows = db.execute('SELECT * FROM workflows ORDER BY workflow_id').fetchall()
        return tuple(self._workflow(row) for row in rows)

    def register_workflow(self, workflow: Workflow, references: dict[str, str]) -> None:
        """Atomically register the index only; no filesystem transaction implied."""
        with self._connection() as db:
            db.execute('INSERT INTO workflows VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (
                require_uuid(workflow.workflow_id), require_uuid(workflow.project_id),
                workflow.name, workflow.specification_path, workflow.specification_hash,
                workflow.approval_id, workflow.state_path, workflow.history_path))
            db.executemany('INSERT INTO artifact_references VALUES (?, ?, ?)',
                [(str(workflow.workflow_id), require_text(role), require_text(path))
                 for role, path in references.items()])

    def set_artifact_references(self, workflow_id: UUID, references: dict[str, str]) -> None:
        self.get_workflow(workflow_id)
        with self._connection() as db:
            db.executemany('''INSERT INTO artifact_references VALUES (?, ?, ?)
                ON CONFLICT(workflow_id, role) DO UPDATE SET path = excluded.path''',
                [(require_uuid(workflow_id), require_text(role), require_text(path))
                 for role, path in references.items()])

    def rename_workflow(self, workflow_id: UUID, name: str) -> None:
        with self._connection() as db:
            changed = db.execute('UPDATE workflows SET name = ? WHERE workflow_id = ?',
                                 (require_text(name), require_uuid(workflow_id)))
            if changed.rowcount != 1:
                raise KeyError(workflow_id)

    def set_artifact_reference(self, workflow_id: UUID, role: str, path: str) -> None:
        with self._connection() as db:
            db.execute('''INSERT INTO artifact_references VALUES (?, ?, ?)
                ON CONFLICT(workflow_id, role) DO UPDATE SET path = excluded.path''',
                (require_uuid(workflow_id), require_text(role), require_text(path)))

    def artifact_references(self, workflow_id: UUID) -> dict[str, str]:
        self.get_workflow(workflow_id)
        with self._connection() as db:
            return dict(db.execute('SELECT role, path FROM artifact_references WHERE workflow_id = ?',
                                   (require_uuid(workflow_id),)).fetchall())
