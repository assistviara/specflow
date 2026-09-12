from dataclasses import FrozenInstanceError

import pytest

from application.implementation_evidence import EvidenceDeviations


def test_evidence_deviations_is_frozen_dataclass() -> None:
    deviations = EvidenceDeviations(
        out_of_scope_changes=(
            "core/example.py",
        ),
        unplanned_changes=(
            "application/unplanned.py",
        ),
        unfinished_items=(
            "full regression not completed",
        ),
        human_approval_required=(
            "scope decision required",
        ),
    )

    assert deviations.out_of_scope_changes == (
        "core/example.py",
    )
    assert deviations.unplanned_changes == (
        "application/unplanned.py",
    )
    assert deviations.unfinished_items == (
        "full regression not completed",
    )
    assert deviations.human_approval_required == (
        "scope decision required",
    )

    with pytest.raises(FrozenInstanceError):
        deviations.unfinished_items = ()


def test_evidence_deviations_accepts_empty_fact_groups() -> None:
    deviations = EvidenceDeviations(
        out_of_scope_changes=(),
        unplanned_changes=(),
        unfinished_items=(),
        human_approval_required=(),
    )

    assert deviations.out_of_scope_changes == ()
    assert deviations.unplanned_changes == ()
    assert deviations.unfinished_items == ()
    assert deviations.human_approval_required == ()
