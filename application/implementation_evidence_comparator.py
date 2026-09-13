from dataclasses import dataclass
from pathlib import PurePath

from application.implementation_evidence import EvidenceScope
from application.implementation_result_parser import ImplementationResult
from application.repository_state_provider import RepositoryState
from application.execution_state_provider import TestState


@dataclass(frozen=True)
class EvidenceComparison:
    missing_evidence: tuple[str, ...]
    inconsistencies: tuple[str, ...]
    out_of_scope_changes: tuple[str, ...]
    unplanned_changes: tuple[str, ...]
    human_approval_required: tuple[str, ...]


class ImplementationEvidenceComparator:
    def compare(
        self,
        *,
        implementation_result: ImplementationResult | None,
        repository_state: RepositoryState,
        test_state: TestState,
        scope: EvidenceScope | None,
        expected_branch: str,
        expected_base_commit: str,
    ) -> EvidenceComparison:
        missing_evidence = (
            repository_state.unavailable_evidence
            + test_state.unavailable_evidence
        )

        if (
            test_state.initial_test_status == "NOT_RUN"
            and test_state.no_tdd_reason is None
        ):
            missing_evidence = (
                missing_evidence
                + ("no TDD reason unavailable",)
            )

        if scope is None:
            missing_evidence = (
                missing_evidence
                + ("approved scope unavailable",)
            )

        if implementation_result is None:
            missing_evidence = (
                missing_evidence
                + ("implementation result unavailable",)
            )
            reported_files = None
        else:
            reported_files = self._reported_files(
                implementation_result.changed_files
            )

        actual_files = tuple(
            dict.fromkeys(
                repository_state.created_files
                + repository_state.modified_files
                + repository_state.deleted_files
            )
        )

        inconsistencies: list[str] = []

        if repository_state.branch != expected_branch:
            inconsistencies.append(
                "implementation branch mismatch: "
                f"expected={expected_branch} "
                f"actual={repository_state.branch}"
            )

        if repository_state.base_commit != expected_base_commit:
            inconsistencies.append(
                "base commit mismatch: "
                f"expected={expected_base_commit} "
                f"actual={repository_state.base_commit}"
            )

        if reported_files is not None:
            actual_set = set(actual_files)
            reported_set = set(reported_files)

            for path in reported_files:
                if path not in actual_set:
                    inconsistencies.append(
                        "reported change not found in actual changes: "
                        f"{path}"
                    )

            for path in actual_files:
                if path not in reported_set:
                    inconsistencies.append(
                        "actual change not reported by Codex: "
                        f"{path}"
                    )

        if scope is None:
            out_of_scope_changes = ()
            unplanned_changes = ()
        else:
            out_of_scope_changes = tuple(
                path
                for path in actual_files
                if self._matches_any(
                    path,
                    scope.forbidden_changes,
                )
            )

            unplanned_changes = tuple(
                path
                for path in actual_files
                if not self._matches_any(
                    path,
                    scope.allowed_changes,
                )
                and path not in out_of_scope_changes
            )

        missing_evidence = tuple(
            dict.fromkeys(missing_evidence)
        )

        human_approval_required: list[str] = []

        if implementation_result is not None:
            codex_human_approval = (
                implementation_result.human_approval_required.strip()
            )

            if (
                codex_human_approval
                and codex_human_approval != "NONE"
            ):
                human_approval_required.append(
                    codex_human_approval
                )

        for item in missing_evidence:
            human_approval_required.append(
                "missing evidence requires human judgment: "
                f"{item}"
            )

        return EvidenceComparison(
            missing_evidence=missing_evidence,
            inconsistencies=tuple(inconsistencies),
            out_of_scope_changes=out_of_scope_changes,
            unplanned_changes=unplanned_changes,
            human_approval_required=tuple(
                dict.fromkeys(human_approval_required)
            ),
        )

    @staticmethod
    def _reported_files(
        changed_files: str,
    ) -> tuple[str, ...]:
        return tuple(
            line.strip()
            for line in changed_files.splitlines()
            if line.strip()
        )

    @staticmethod
    def _matches_any(
        path: str,
        patterns: tuple[str, ...],
    ) -> bool:
        candidate = PurePath(path)

        return any(
            candidate.match(pattern)
            for pattern in patterns
        )
