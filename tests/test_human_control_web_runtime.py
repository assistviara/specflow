from pathlib import Path
import sqlite3
from uuid import uuid4

import pytest

from app import create_app
from human_control.sqlite_repository import HumanControlRepository
from human_control.web_runtime import Runtime, BoundaryError, parse_uuid
from human_control.application_adapter import WorkflowObservation
from human_control.models import Project, Workflow


@pytest.fixture
def db(tmp_path):
    path = tmp_path / 'control.sqlite3'
    HumanControlRepository.initialize(path)
    return path


def test_explicit_database_open_and_no_implicit_creation(db, tmp_path):
    app = create_app(db)
    assert app.extensions['human_control'].require_repository().path == db
    missing = tmp_path / 'missing.db'
    failed = create_app(missing)
    response = failed.test_client().get('/')
    assert response.status_code == 503
    assert str(missing) in response.get_data(as_text=True)
    assert not missing.exists()
    with pytest.raises(BoundaryError):
        failed.extensions['human_control'].require_repository()
    assert create_app().test_client().get('/').status_code == 503


@pytest.mark.parametrize('pragma,value', [('user_version', 4), ('application_id', 0)])
def test_incompatible_database_unchanged(db, pragma, value):
    with sqlite3.connect(db) as connection:
        connection.execute(f'PRAGMA {pragma} = {value}')
    before = db.read_bytes()
    runtime = Runtime(db)
    assert runtime.failure.path == str(db)
    assert runtime.failure.reason
    with pytest.raises(BoundaryError):
        runtime.require_repository()
    assert db.read_bytes() == before


def test_failure_does_not_expose_exception_secret(db, monkeypatch):
    def fail(path):
        raise OSError('secret=DO_NOT_DISPLAY')
    monkeypatch.setattr('human_control.web_runtime.HumanControlRepository', fail)
    response = create_app(db).test_client().get('/')
    assert response.status_code == 503
    assert 'DO_NOT_DISPLAY' not in response.get_data(as_text=True)
    assert '自動' in response.get_data(as_text=True)


def test_explicit_initialization_cli_and_existing_file_preserved(tmp_path):
    path = tmp_path / 'new.db'
    app = create_app(path)
    runner = app.test_cli_runner()
    assert runner.invoke(args=['init-human-control-db', '--path', str(path)]).exit_code == 0
    assert HumanControlRepository(path)
    before = path.read_bytes()
    assert runner.invoke(args=['init-human-control-db', '--path', str(path)]).exit_code != 0
    assert path.read_bytes() == before


def test_initialization_failure_retains_partial_file(tmp_path, monkeypatch):
    path = tmp_path / 'partial.db'
    def fail(path):
        Path(path).write_bytes(b'partial')
        raise OSError('private diagnostic')
    monkeypatch.setattr(HumanControlRepository, 'initialize', fail)
    result = create_app().test_cli_runner().invoke(args=['init-human-control-db', '--path', str(path)])
    assert result.exit_code != 0
    assert path.read_bytes() == b'partial'
    assert 'private diagnostic' not in result.output


@pytest.mark.parametrize('value', ['Project name', '../project', '', None, 12])
def test_invalid_identity(value):
    with pytest.raises(BoundaryError):
        parse_uuid(value)


def test_uuid_and_ownership(db):
    runtime = Runtime(db)
    p, w, other = uuid4(), uuid4(), uuid4()
    repo = runtime.require_repository()
    repo.add_project(Project(p, 'Human name'))
    repo.add_project(Project(other, 'Other'))
    repo.add_workflow(Workflow(w, p, 'Work', '/spec', 'a' * 64, 'approval', '/state', '/history'))
    assert parse_uuid(str(p)) == p
    assert parse_uuid(w) == w
    assert runtime.target(str(p), str(w)) == (p, w)
    with pytest.raises(BoundaryError):
        runtime.target(other, w)
    with pytest.raises(BoundaryError):
        runtime.target(uuid4())


def test_token_session_target_revision_replay_and_get(db):
    app = create_app(db)
    tokens = app.extensions['human_control'].forms
    p, w = uuid4(), uuid4()
    with app.test_request_context('/', method='GET'):
        token = tokens.issue('save', p, w, revision='observed-artifact-hash')
        from flask import session
        cookie = dict(session)
        with pytest.raises(BoundaryError):
            tokens.consume(token, 'save', p, w, revision='observed-artifact-hash')
    with app.test_request_context('/', method='POST'):
        session.update(cookie)
        tokens.consume(token, 'save', p, w, revision='observed-artifact-hash')
        with pytest.raises(BoundaryError):
            tokens.consume(token, 'save', p, w, revision='observed-artifact-hash')


@pytest.mark.parametrize('fault', ['missing', 'invalid', 'target', 'action', 'stale', 'session', 'process'])
def test_token_rejects_bad_context(db, fault):
    app = create_app(db)
    tokens = app.extensions['human_control'].forms
    p, w = uuid4(), uuid4()
    from flask import session
    with app.test_request_context('/', method='POST'):
        token = tokens.issue('save', p, w, revision='v1')
        if fault == 'session':
            session.clear()
        if fault == 'process':
            tokens = Runtime(db).forms
        with pytest.raises(BoundaryError):
            tokens.consume(None if fault == 'missing' else 'bad' if fault == 'invalid' else token,
                'other' if fault == 'action' else 'save',
                uuid4() if fault == 'target' else p, w,
                revision='v2' if fault == 'stale' else 'v1')


def test_output_holder_detached_scoped_clear_and_restart(db):
    runtime = Runtime(db)
    p, w, w2 = uuid4(), uuid4(), uuid4()
    observation = WorkflowObservation(p, w, ({'actual': ['result']},))
    runtime.outputs.put(observation)
    observation.outputs[0]['actual'].clear()
    assert runtime.outputs.get(p, w).outputs[0]['actual'] == ['result']
    assert runtime.outputs.get(p, w2) is None
    with pytest.raises(BoundaryError):
        runtime.outputs.get(uuid4(), w)
    assert Runtime(db).outputs.get(p, w) is None
    assert not runtime.outputs.get(p, w).outputs[0].get('state')
    runtime.outputs.clear(w)
    assert runtime.outputs.get(p, w) is None
    with pytest.raises(BoundaryError):
        runtime.outputs.put({'state': 'completed'})


def test_failure_blocks_post_before_legacy_write(tmp_path, monkeypatch):
    def forbidden(*args):
        pytest.fail('Write must not be reached while DB is unavailable')
    monkeypatch.setattr('app.save_text', forbidden)
    response = create_app(tmp_path / 'missing.db').test_client().post(
        '/projects/example', data={'specification': 'must not save'})
    assert response.status_code == 503


def test_valid_get_preserves_database_and_legacy_links(db, monkeypatch, tmp_path):
    monkeypatch.setattr('app.PROJECTS_DIR', tmp_path / 'legacy')
    before = db.read_bytes()
    client = create_app(db).test_client()
    assert client.get('/').status_code == 200
    assert client.get('/projects/example').status_code == 200
    assert db.read_bytes() == before
    assert not (tmp_path / 'legacy').exists()


def test_new_form_invalidates_previous_and_token_is_not_authority(db):
    app = create_app(db)
    runtime = app.extensions['human_control']
    p, w = uuid4(), uuid4()
    before = db.read_bytes()
    with app.test_request_context('/', method='POST'):
        old = runtime.forms.issue('save', p, w, revision='v1')
        new = runtime.forms.issue('save', p, w, revision='v1')
        with pytest.raises(BoundaryError):
            runtime.forms.consume(old, 'save', p, w, revision='v1')
        runtime.forms.consume(new, 'save', p, w, revision='v1')
        # Token acceptance cannot establish a Project or Workflow in the DB.
        with pytest.raises(BoundaryError):
            runtime.target(p, w)
    assert db.read_bytes() == before


def test_failure_template_escapes_path(db, monkeypatch):
    from human_control.web_runtime import DatabaseFailure
    app = create_app(db)
    app.extensions['human_control'].failure = DatabaseFailure('<script>bad</script>', 'reason')
    body = app.test_client().get('/').get_data(as_text=True)
    assert '<script>bad</script>' not in body
    assert '&lt;script&gt;' in body
