"""Persistence boundary for Phase 6 merge retry events, separate from State."""
from typing import Protocol


class MergeRetryRepository(Protocol):
    def read(self, operation_id: str, event: str) -> dict | None:
        ...

    def create(self, operation_id: str, event: str, value: dict) -> None:
        """Durably create exactly once; existing or uncertain writes must fail."""
        ...
