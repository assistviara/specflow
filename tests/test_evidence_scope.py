from dataclasses import FrozenInstanceError

import pytest

from application.implementation_evidence import EvidenceScope


def test_evidence_scope_is_frozen_dataclass() -> None:
    scope = EvidenceScope(
        target_paths=(
            "application/**",
            "tests/**",
        ),
        allowed_changes=(
            "application/**",
            "tests/**",
        ),
        forbidden_changes=(
            "core/**",
        ),
    )

    assert scope.target_paths == (
        "application/**",
        "tests/**",
    )
    assert scope.allowed_changes == (
        "application/**",
        "tests/**",
    )
    assert scope.forbidden_changes == (
        "core/**",
    )

    with pytest.raises(FrozenInstanceError):
        scope.target_paths = ()


def test_evidence_scope_accepts_empty_rule_groups() -> None:
    scope = EvidenceScope(
        target_paths=(),
        allowed_changes=(),
        forbidden_changes=(),
    )

    assert scope.target_paths == ()
    assert scope.allowed_changes == ()
    assert scope.forbidden_changes == ()
