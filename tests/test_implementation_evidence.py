from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from application.implementation_evidence import ImplementationEvidence


def test_implementation_evidence_is_frozen_dataclass_with_required_blocks() -> None:
    evidence = ImplementationEvidence(
        identity={"evidence_id": str(uuid4())},
        basis={},
        scope={},
        changes={},
        verification={},
        deviations={},
        codex_summary={},
    )

    assert evidence.identity
    assert evidence.basis == {}
    assert evidence.scope == {}
    assert evidence.changes == {}
    assert evidence.verification == {}
    assert evidence.deviations == {}
    assert evidence.codex_summary == {}

    with pytest.raises(FrozenInstanceError):
        evidence.identity = {}
