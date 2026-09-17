import json
from pathlib import Path
from uuid import UUID

from application.execution_record import (
    TestExecutionRecord,
)
from application.execution_record_serializer import (
    execution_record_from_dict,
    execution_record_to_dict,
)


class JsonTestExecutionRecordRepository:
    def __init__(
        self,
        evidence_dir: Path,
    ) -> None:
        self._evidence_dir = evidence_dir

    def save(
        self,
        record: TestExecutionRecord,
    ) -> Path:
        self._evidence_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        path = self._json_path(
            record.implementation_id
        )

        if path.exists():
            raise FileExistsError(path)

        data = execution_record_to_dict(record)

        path.write_text(
            json.dumps(
                data,
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        return path

    def load(
        self,
        implementation_id: UUID,
    ) -> TestExecutionRecord:
        path = self._json_path(implementation_id)

        if not path.exists():
            raise FileNotFoundError(path)

        data = json.loads(
            path.read_text(encoding="utf-8")
        )

        return execution_record_from_dict(data)

    def exists(
        self,
        implementation_id: UUID,
    ) -> bool:
        return self._json_path(
            implementation_id
        ).exists()

    def _json_path(
        self,
        implementation_id: UUID,
    ) -> Path:
        return (
            self._evidence_dir
            / f"test_execution_{implementation_id}.json"
        )
