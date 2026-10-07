"""Initial Plan only: inspect a fixed Repository and return text without saving it."""
from pathlib import Path
import json

from core.ai.ai_response import AIResponse
from core.ai.ai_request import AIRequest
from infrastructure.codex_jsonl_parser import parse_codex_jsonl
from infrastructure.plan_repository_snapshot import PlanRepositorySnapshotProvider, SnapshotUnavailable


class PlanCodexRunner:
    def __init__(self, command_executor, repository: Path, repository_validator,
                 snapshot_provider=None):
        if not callable(repository_validator):
            raise ValueError('Plan Repository validation is required')
        self._command_executor = command_executor
        self._repository = Path(repository)
        self._repository_validator = repository_validator
        self._snapshots = snapshot_provider or PlanRepositorySnapshotProvider(self._repository)

    @staticmethod
    def _failure(reason):
        return AIResponse(content='', success=False, error_message=reason)

    def run(self, request: AIRequest) -> AIResponse:
        try:
            if not self._repository.is_absolute() or not self._repository.is_dir():
                raise ValueError('Repository directory unavailable')
            self._repository_validator(str(self._repository))
        except Exception:
            return self._failure('Plan Repository validation failed; STOP.')
        try:
            before = self._snapshots.capture()
        except Exception as exc:
            return self._observation_failure('before', exc)
        raw = None
        execution_failed = False
        try:
            raw = self._command_executor.run(
                ['codex', '--ask-for-approval', 'never', 'exec', '--sandbox', 'read-only',
                 '--json', '--ephemeral', '-'],
                cwd=self._repository,
                input_text=('Inspect the configured Repository to generate the Implementation Plan. '
                            'Return only the Plan body in your final response. Do not save, edit, '
                            'create or delete files, implement changes, or request write permissions.\n\n'
                            + request.prompt),
            )
        except Exception:
            execution_failed = True
        try:
            after = self._snapshots.capture()
            changes = before.differences(after)
        except Exception as exc:
            return self._observation_failure('after', exc)
        if changes:
            return self._failure('Repository state changed; STOP: ' + ', '.join(changes))
        if execution_failed:
            return self._failure('Plan Codex process failed; STOP.')
        try:
            parsed = parse_codex_jsonl(raw)
            if (not parsed.process_succeeded or parsed.errors
                    or not isinstance(parsed.final_message, str) or not parsed.final_message.strip()):
                return self._failure('Plan Codex JSONL completion or final body invalid; STOP.')
            # The shared parser ignores error events with missing messages.
            for line in raw.splitlines():
                if not line.strip():
                    continue
                event = json.loads(line)
                if not isinstance(event, dict) or not isinstance(event.get('type'), str):
                    return self._failure('Plan Codex JSONL event invalid; STOP.')
                if event.get('type') in ('error', 'turn.failed') or (
                        isinstance(event.get('item'), dict) and event['item'].get('type') == 'error'):
                    return self._failure('Plan Codex JSONL contains an error; STOP.')
            return AIResponse(content=parsed.final_message, success=True)
        except Exception:
            return self._failure('Plan Codex JSONL invalid; STOP.')

    def _observation_failure(self, phase, exc):
        detail = str(exc) if isinstance(exc, SnapshotUnavailable) else 'snapshot observation unavailable'
        return self._failure(f'Repository comparison unavailable ({phase}): {detail}; STOP.')
