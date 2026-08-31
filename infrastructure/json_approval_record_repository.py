import json
from pathlib import Path

from core.approval_record_repository import ApprovalRecordRepository


class JsonApprovalRecordRepository(ApprovalRecordRepository):
    def __init__(self, approvals_dir: Path) -> None:
        self.approvals_dir = approvals_dir

    def save(self, record: dict) -> None:
        self.approvals_dir.mkdir(parents=True, exist_ok=True)

        approval_id = record["approval_id"]
        approval_file = self.approvals_dir / f"{approval_id}.json"

        approval_file.write_text(
            json.dumps(record, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get(self, approval_id: str) -> dict:
        approval_file = self.approvals_dir / f"{approval_id}.json"

        return json.loads(
            approval_file.read_text(encoding="utf-8")
        )