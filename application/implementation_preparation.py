from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class PreparedImplementation:
    repository: Path
    base_branch: str
    base_commit: str
    implementation_branch: str


class ImplementationPreparation(Protocol):
    def prepare(self, repository: Path, branch: str) -> PreparedImplementation:
        ...
