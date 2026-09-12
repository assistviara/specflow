def resolve_evidence_status(
    missing_evidence: tuple[str, ...],
) -> str:
    if missing_evidence:
        return "PARTIAL"

    return "COLLECTED"
