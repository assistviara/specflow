"""Read-only decision material after creation; never an Approval or checkpoint."""
import json
from pathlib import Path
from uuid import UUID


class JsonHumanApprovalRequestRepository:
    def __init__(self, directory):
        self.directory = Path(directory)

    @staticmethod
    def validate(record, project_id, workflow_id):
        if record['version'] != 1:
            raise ValueError('Unsupported approval request version')
        for key in ('project_id', 'workflow_id', 'implementation_id'):
            if str(UUID(record[key])) != record[key]:
                raise ValueError('Invalid approval request identity')
        if (record['project_id'], record['workflow_id']) != (str(project_id), str(workflow_id)):
            raise ValueError('Approval request ownership mismatch')
        if not isinstance(record['body'], str) or record['body'].strip() in ('', 'NONE'):
            raise ValueError('Additional approval request body required')

    def save(self, record):
        self.validate(record, record['project_id'], record['workflow_id'])
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.directory / (record['implementation_id'] + '.json')
        try:
            with path.open('x', encoding='utf-8') as stream:
                json.dump(record, stream, ensure_ascii=False, indent=2)
        except FileExistsError:
            old = json.loads(path.read_text(encoding='utf-8'))
            if any(old.get(key) != value for key, value in record.items() if key != 'recorded_at'):
                raise ValueError('Approval request collision; existing record retained')
        return path

    def load_all(self, project_id, workflow_id):
        records = []
        for path in sorted(self.directory.glob('*.json')):
            record = json.loads(path.read_text(encoding='utf-8'))
            self.validate(record, project_id, workflow_id)
            if path.stem != record['implementation_id']:
                raise ValueError('Approval request filename mismatch')
            records.append(record)
        return records
