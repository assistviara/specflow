from abc import ABC, abstractmethod


class ApprovalRecordRepository(ABC):
    @abstractmethod
    def save(self, record: dict) -> None:
        pass

    @abstractmethod
    def get(self, approval_id: str) -> dict:
        pass