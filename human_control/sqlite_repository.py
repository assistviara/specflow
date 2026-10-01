"""Small SQLite index. No Artifact IO, approval decisions or State transitions."""
from contextlib import contextmanager
from pathlib import Path
import sqlite3
from uuid import UUID

from human_control.models import Project, Workflow, require_text, require_uuid


_SCHEMA = (
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


class HumanControlRepository:
    def __init__(self, path: Path):
        self.path = Path(path).resolve()
        # Opening never creates or upgrades a database.
        with self._connection() as db:
            if (db.execute('PRAGMA application_id').fetchone()[0] != _APPLICATION_ID
                    or db.execute('PRAGMA user_version').fetchone()[0] != 1):
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
                db.execute('PRAGMA user_version = 1')
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

    def add_project(self, project: Project) -> None:
        with self._connection() as db:
            db.execute('INSERT INTO projects VALUES (?, ?)',
                       (require_uuid(project.project_id), project.name))

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
