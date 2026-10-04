from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import Mock
import sys

import pytest

from infrastructure.subprocess_command_executor import SubprocessCommandExecutor
from core.ai.codex_runner import CodexRunner
from application.codex_implementation_adapter import CodexImplementationAdapter
from infrastructure.codex_jsonl_parser import parse_codex_jsonl


def test_exact_codex_command_cwd_stdin_and_jsonl_stderr_boundary(monkeypatch, tmp_path):
    raw = '{"type":"turn.completed"}\n'
    run = Mock(return_value=CompletedProcess([], 0, raw, 'stderr must not enter trace'))
    monkeypatch.setattr('subprocess.run', run)
    runner = CodexRunner(SubprocessCommandExecutor())
    assert runner.run(prompt='Human prompt\n日本語', working_directory=tmp_path) == raw
    run.assert_called_once_with(['codex', 'exec', '--json', '--ephemeral', '-'], cwd=tmp_path,
        input='Human prompt\n日本語', shell=False, capture_output=True, text=True,
        encoding='utf-8', check=False)


@pytest.mark.parametrize('error', [FileNotFoundError('secret'), PermissionError('secret'), UnicodeError('secret')])
def test_start_decode_failure_is_stop_without_secret(monkeypatch, error):
    monkeypatch.setattr('subprocess.run', Mock(side_effect=error))
    with pytest.raises(RuntimeError, match='STOP') as caught:
        SubprocessCommandExecutor().run(['codex'], cwd=Path('.'), input_text='private')
    assert 'secret' not in str(caught.value)


@pytest.mark.parametrize('code', [1, -1, 127])
def test_nonzero_exit_cannot_be_hidden_by_success_jsonl(monkeypatch, code):
    monkeypatch.setattr('subprocess.run', Mock(return_value=CompletedProcess(
        [], code, '{"type":"turn.completed"}\n', 'secret stderr')))
    with pytest.raises(RuntimeError, match=f'exit {code}') as caught:
        SubprocessCommandExecutor().run(['codex'], cwd=Path('.'), input_text='private')
    assert 'secret' not in str(caught.value)


@pytest.mark.parametrize('raw', ['', 'not JSON', '{"type":"turn.failed"}\n'])
def test_transport_does_not_fabricate_valid_jsonl(monkeypatch, raw):
    monkeypatch.setattr('subprocess.run', Mock(return_value=CompletedProcess([], 0, raw, '')))
    adapter = CodexImplementationAdapter(CodexRunner(SubprocessCommandExecutor()), trace_parser=parse_codex_jsonl)
    result = adapter.run(prompt='explicit', working_directory=Path('.'))
    assert result.raw_jsonl == raw
    assert not result.process_succeeded or result.errors or result.final_message is None


def test_real_local_process_transport_without_ai_or_git(tmp_path):
    script = 'import sys; print(sys.stdin.read(), end=""); print("diagnostic", file=sys.stderr)'
    raw = '{"type":"turn.completed"}\n'
    result = SubprocessCommandExecutor().run([sys.executable, '-c', script], cwd=tmp_path, input_text=raw)
    assert result == raw


def test_real_local_nonzero_process_stops(tmp_path):
    with pytest.raises(RuntimeError, match='exit 3'):
        SubprocessCommandExecutor().run([sys.executable, '-c', 'raise SystemExit(3)'],
                                       cwd=tmp_path, input_text='')
