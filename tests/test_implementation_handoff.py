import hashlib
from types import SimpleNamespace
from uuid import uuid4

import pytest

from application.execute_implementation import ExecuteImplementationUseCase
from application.dto import ExecuteImplementationInput
from application.codex_implementation_adapter import CodexImplementationAdapter


@pytest.mark.parametrize('changed', [False, True, 'unreadable', 'invalid_utf8'])
def test_approved_document_bytes_reach_runner_or_stop(tmp_path, monkeypatch, changed):
    import application.execute_implementation as module
    paths = [tmp_path / 'spec.md', tmp_path / 'plan.md']
    bodies = ['仕様\r\n## Scope\r\n全文', '計画\n```text\n手順\n```']
    records = {}
    for path, body, kind in zip(paths, bodies, ['specification', 'implementation_plan']):
        raw = body.encode('utf-8')
        path.write_bytes(raw)
        records[kind] = dict(approval_id=kind, artifact_type=kind,
                             artifact_path=str(path), artifact_hash=hashlib.sha256(raw).hexdigest(),
                             decision='approved')
    state = tmp_path / 'state.json'
    state.write_text('{"status":"implementation_ready"}')
    received = []
    def run(**kwargs):
        received.append(kwargs['prompt'])
        raise RuntimeError('test capture only')
    original = module.validate_approval_result
    def validate(*args):
        result = original(*args)
        if changed and args[2] == 'implementation_plan':
            if changed == 'unreadable':
                original_read = type(paths[0]).read_bytes
                def read(path):
                    if path == paths[0]:
                        raise PermissionError('denied')
                    return original_read(path)
                monkeypatch.setattr(type(paths[0]), 'read_bytes', read)
            elif changed == 'invalid_utf8':
                paths[0].write_bytes(b'\xff')
                records['specification']['artifact_hash'] = hashlib.sha256(b'\xff').hexdigest()
            else:
                paths[0].write_text('changed after validation')
        return result
    monkeypatch.setattr(module, 'validate_approval_result', validate)
    request = ExecuteImplementationInput(
        base_branch='developer', implementation_id=uuid4(),
        specification_path=paths[0], specification_approval_id='specification',
        implementation_plan_path=paths[1], implementation_plan_approval_id='implementation_plan',
        codex_prompt='AI summary only', codex_prompt_specification_path=paths[0],
        codex_prompt_implementation_plan_path=paths[1], implementation_branch='implementation/test',
        base_commit='abc', working_directory=tmp_path, state_file=state,
        state_history_dir=tmp_path / 'history')
    output = ExecuteImplementationUseCase(SimpleNamespace(get=records.get),
        SimpleNamespace(run=run)).execute(request)
    if changed:
        assert received == []
        assert not output.success
        assert state.read_text() == '{"status":"implementation_ready"}'
    else:
        assert len(received) == 1
        for path, body in zip(paths, bodies):
            assert body in received[0]
            assert str(path) in received[0]
        for record in records.values():
            assert record['artifact_hash'] in received[0]
            assert record['approval_id'] in received[0]


def test_wrapper_environment_is_explicit_without_mutating_environment(tmp_path, monkeypatch):
    monkeypatch.delenv('PYTHONPATH', raising=False)
    import os
    received = []
    adapter = CodexImplementationAdapter(
        SimpleNamespace(run=lambda **kw: received.append(kw) or 'raw'),
        trace_parser=lambda raw: raw,
        test_environment=(tmp_path / 'venv' / 'python.exe', tmp_path / 'SpecFlow'))
    assert adapter.run(prompt='scope', working_directory=tmp_path) == 'raw'
    prompt = received[0]['prompt']
    assert str(tmp_path / 'venv' / 'python.exe') in prompt
    assert str(tmp_path / 'SpecFlow') in prompt
    assert 'PYTHONPATH' in prompt
    assert 'infrastructure.specflow_test_wrapper --phase' in prompt
    assert received[0]['working_directory'] == tmp_path
    assert 'PYTHONPATH' not in os.environ
