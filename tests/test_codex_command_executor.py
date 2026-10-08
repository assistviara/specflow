"""Offline executable resolution and transparent transport delegation."""
import os
from pathlib import Path
from unittest.mock import Mock

import pytest

from infrastructure import codex_command_executor as module


@pytest.fixture
def windows(monkeypatch):
    monkeypatch.setattr(module.sys, 'platform', 'win32')


def test_windows_replaces_only_executable_and_preserves_values(windows, monkeypatch, tmp_path):
    directory = tmp_path / 'npm 日本語 path'
    directory.mkdir()
    executable = directory / 'codex.cmd'
    executable.write_text('offline fixture', encoding='utf-8')
    monkeypatch.setenv('PATH', str(directory))
    transport = Mock()
    transport.run.return_value = 'result'
    command = ['codex', 'exec', '--json', 'argument with spaces', '日本語', '-']
    original = command.copy()
    cwd = tmp_path / 'repository 日本語'
    stdin = 'private prompt\n日本語'
    assert module.CodexCommandExecutor(transport).run(command, cwd=cwd, input_text=stdin) == 'result'
    transport.run.assert_called_once_with([str(executable.resolve()), *original[1:]],
                                          cwd=cwd, input_text=stdin)
    passed = transport.run.call_args
    assert Path(passed.args[0][0]).is_absolute()
    assert passed.kwargs['cwd'] is cwd
    assert passed.kwargs['input_text'] is stdin
    assert command == original
    assert passed.args[0] is not command


@pytest.mark.parametrize('path', ['', '.', 'relative', os.pathsep.join(['', '.', 'relative'])])
def test_relative_and_empty_path_never_resolve_from_cwd(windows, monkeypatch, tmp_path, path):
    (tmp_path / 'codex.cmd').write_text('offline fixture')
    relative = tmp_path / 'relative'
    relative.mkdir()
    (relative / 'codex.cmd').write_text('offline fixture')
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('PATH', path)
    transport = Mock()
    with pytest.raises(RuntimeError, match='STOP'):
        module.CodexCommandExecutor(transport).run(['codex'], cwd=tmp_path, input_text='secret')
    transport.run.assert_not_called()


def test_missing_executable_stops_without_sensitive_values(windows, monkeypatch, tmp_path):
    secret_directory = tmp_path / 'secret environment value'
    secret_directory.mkdir()
    monkeypatch.setenv('PATH', str(secret_directory))
    transport = Mock()
    with pytest.raises(RuntimeError) as caught:
        module.CodexCommandExecutor(transport).run(['codex', 'secret credential'],
                                                 cwd=tmp_path, input_text='secret prompt')
    assert str(caught.value) == 'Codex executable could not be safely resolved; STOP.'
    assert caught.value.__cause__ is None
    transport.run.assert_not_called()


def test_resolution_error_is_sanitized(windows, monkeypatch, tmp_path):
    monkeypatch.setenv('PATH', str(tmp_path))
    monkeypatch.setattr(module.Path, 'is_file', Mock(side_effect=OSError('secret environment')))
    transport = Mock()
    with pytest.raises(RuntimeError, match='STOP') as caught:
        module.CodexCommandExecutor(transport).run(['codex'], cwd=tmp_path, input_text='private')
    assert 'secret' not in str(caught.value)
    transport.run.assert_not_called()


def test_non_windows_preserves_codex_argv(monkeypatch, tmp_path):
    monkeypatch.setattr(module.sys, 'platform', 'linux')
    resolve = Mock(side_effect=AssertionError('Windows resolution must not run'))
    monkeypatch.setattr(module.CodexCommandExecutor, '_resolve_windows_executable', resolve)
    transport = Mock()
    command = ['codex', 'exec', '--json', '--ephemeral', '-']
    module.CodexCommandExecutor(transport).run(command, cwd=tmp_path, input_text='prompt')
    transport.run.assert_called_once_with(command, cwd=tmp_path, input_text='prompt')
    resolve.assert_not_called()


def test_transport_failure_is_preserved_without_retry(windows, monkeypatch, tmp_path):
    (tmp_path / 'codex.cmd').write_text('offline fixture')
    monkeypatch.setenv('PATH', str(tmp_path))
    failure = RuntimeError('Codex process failed (exit 1); STOP.')
    transport = Mock()
    transport.run.side_effect = failure
    with pytest.raises(RuntimeError) as caught:
        module.CodexCommandExecutor(transport).run(['codex'], cwd=tmp_path, input_text='prompt')
    assert caught.value is failure
    transport.run.assert_called_once()


def test_construction_does_not_resolve_or_launch(monkeypatch):
    process = Mock(side_effect=AssertionError('No launch'))
    resolve = Mock(side_effect=AssertionError('No resolution'))
    monkeypatch.setattr('subprocess.run', process)
    monkeypatch.setattr(module.CodexCommandExecutor, '_resolve_windows_executable', resolve)
    transport = Mock()
    module.CodexCommandExecutor(transport)
    resolve.assert_not_called()
    process.assert_not_called()
    transport.run.assert_not_called()
