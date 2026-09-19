from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from application.implementation_evidence import EvidenceIdentity


VALID_CREATED_AT = datetime(
    2026,
    9,
    12,
    8,
    30,
    tzinfo=timezone.utc,
)


def test_evidence_identity_is_frozen_dataclass() -> None:
    evidence_id = uuid4()
    implementation_id = uuid4()
    previous_evidence_id = uuid4()

    identity = EvidenceIdentity(
        evidence_id=evidence_id,
        implementation_id=implementation_id,
        implementation_kind="CORRECTION",
        previous_evidence_id=previous_evidence_id,
        status="COLLECTED",
        created_at=VALID_CREATED_AT,
    )

    assert isinstance(identity.evidence_id, UUID)
    assert isinstance(identity.implementation_id, UUID)
    assert identity.implementation_kind == "CORRECTION"
    assert identity.previous_evidence_id == previous_evidence_id
    assert identity.status == "COLLECTED"
    assert identity.created_at == VALID_CREATED_AT

    with pytest.raises(FrozenInstanceError):
        identity.status = "PARTIAL"


@pytest.mark.parametrize(
    ("implementation_kind", "status", "previous_evidence_id_required"),
    [
        ("INITIAL", "COLLECTED", False),
        ("CORRECTION", "PARTIAL", True),
        ("REIMPLEMENTATION", "COLLECTED", True),
    ],
)
def test_evidence_identity_accepts_defined_values(
    implementation_kind: str,
    status: str,
    previous_evidence_id_required: bool,
) -> None:
    previous_evidence_id = (
        uuid4() if previous_evidence_id_required else None
    )

    identity = EvidenceIdentity(
        evidence_id=uuid4(),
        implementation_id=uuid4(),
        implementation_kind=implementation_kind,
        previous_evidence_id=previous_evidence_id,
        status=status,
        created_at=VALID_CREATED_AT,
    )

    assert identity.implementation_kind == implementation_kind
    assert identity.status == status
    assert identity.previous_evidence_id == previous_evidence_id
    assert identity.created_at == VALID_CREATED_AT


@pytest.mark.parametrize(
    ("implementation_kind", "status"),
    [
        ("UNKNOWN", "COLLECTED"),
        ("INITIAL", "ERROR"),
    ],
)
def test_evidence_identity_rejects_undefined_values(
    implementation_kind: str,
    status: str,
) -> None:
    with pytest.raises(ValueError):
        EvidenceIdentity(
            evidence_id=uuid4(),
            implementation_id=uuid4(),
            implementation_kind=implementation_kind,
            previous_evidence_id=None,
            status=status,
            created_at=VALID_CREATED_AT,
        )


def test_initial_evidence_rejects_previous_evidence_id() -> None:
    with pytest.raises(ValueError):
        EvidenceIdentity(
            evidence_id=uuid4(),
            implementation_id=uuid4(),
            implementation_kind="INITIAL",
            previous_evidence_id=uuid4(),
            status="COLLECTED",
            created_at=VALID_CREATED_AT,
        )


@pytest.mark.parametrize(
    "implementation_kind",
    [
        "CORRECTION",
        "REIMPLEMENTATION",
    ],
)
def test_non_initial_evidence_requires_previous_evidence_id(
    implementation_kind: str,
) -> None:
    with pytest.raises(ValueError):
        EvidenceIdentity(
            evidence_id=uuid4(),
            implementation_id=uuid4(),
            implementation_kind=implementation_kind,
            previous_evidence_id=None,
            status="COLLECTED",
            created_at=VALID_CREATED_AT,
        )


def test_evidence_identity_requires_timezone_aware_created_at() -> None:
    created_at = datetime(
        2026,
        9,
        12,
        8,
        30,
        tzinfo=timezone.utc,
    )

    identity = EvidenceIdentity(
        evidence_id=uuid4(),
        implementation_id=uuid4(),
        implementation_kind="INITIAL",
        previous_evidence_id=None,
        status="COLLECTED",
        created_at=created_at,
    )

    assert identity.created_at == created_at
    assert identity.created_at.tzinfo is not None
    assert identity.created_at.utcoffset() is not None


def test_evidence_identity_rejects_naive_created_at() -> None:
    with pytest.raises(ValueError):
        EvidenceIdentity(
            evidence_id=uuid4(),
            implementation_id=uuid4(),
            implementation_kind="INITIAL",
            previous_evidence_id=None,
            status="COLLECTED",
            created_at=datetime(2026, 9, 12, 8, 30),
        )
