from pathlib import Path
from typing import Protocol
from uuid import UUID

from application.execution_record import (
    TestExecutionRecord,
)


class TestExecutionRecordRepository(Protocol):
    def save(
        self,
        record: TestExecutionRecord,
    ) -> Path:
        ...

    def load(
        self,
        implementation_id: UUID,
    ) -> TestExecutionRecord:
        ...

    def exists(
        self,
        implementation_id: UUID,
    ) -> bool:
        ...
