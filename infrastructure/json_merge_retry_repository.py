"""Append-only Phase 6 retry journal. No counter reset or event overwrite."""
import json
import os
from pathlib import Path
from uuid import UUID


class JsonMergeRetryRepository:
    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def _path(self, operation_id: str, event: str) -> Path:
        if str(UUID(operation_id)) != operation_id:
            raise ValueError('Canonical operation UUID required')
        if event not in ('registration', 'operation', 'initial', 'authorization', 'attempt', 'result'):
            raise ValueError('Unknown merge retry event')
        return self._directory / operation_id / (event + '.json')

    def read(self, operation_id: str, event: str) -> dict | None:
        path = self._path(operation_id, event)
        try:
            value = json.loads(path.read_text(encoding='utf-8'))
        except FileNotFoundError:
            return None
        if not isinstance(value, dict):
            raise ValueError('Invalid merge retry event')
        return value

    def create(self, operation_id: str, event: str, value: dict) -> None:
        path = self._path(operation_id, event)
        content = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode('utf-8')
        path.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation is also the cross-process claim for the retry slot.
        # A partial/unreadable file remains a consumed/unknown claim, never reusable.
        with path.open('xb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
