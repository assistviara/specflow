from application.evidence_status_resolver import resolve_evidence_status


def test_resolve_evidence_status_returns_collected_when_missing_evidence_is_empty() -> None:
    status = resolve_evidence_status(
        missing_evidence=(),
    )

    assert status == "COLLECTED"


def test_resolve_evidence_status_returns_partial_when_missing_evidence_exists() -> None:
    status = resolve_evidence_status(
        missing_evidence=("approved scope unavailable",),
    )

    assert status == "PARTIAL"
