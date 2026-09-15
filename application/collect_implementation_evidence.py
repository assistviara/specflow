from datetime import datetime
from uuid import uuid4

from application.dto import (
    CollectImplementationEvidenceInput,
    CollectImplementationEvidenceOutput,
)
from application.evidence_status_resolver import (
    resolve_evidence_status,
)
from application.implementation_evidence import (
    EvidenceChanges,
    EvidenceCodexSummary,
    EvidenceDeviations,
    EvidenceIdentity,
    EvidenceVerification,
    ImplementationEvidence,
)
from application.implementation_evidence_basis_builder import (
    ImplementationEvidenceBasisBuilder,
)
from application.implementation_evidence_comparator import (
    ImplementationEvidenceComparator,
)


def _normalized_lines(value: str) -> tuple[str, ...]:
    return tuple(
        line.strip()
        for line in value.splitlines()
        if line.strip()
    )


def _normalized_optional_lines(value: str) -> tuple[str, ...]:
    lines = _normalized_lines(value)

    if lines == ("NONE",):
        return ()

    return lines


def _deduplicated(
    *groups: tuple[str, ...],
) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            item
            for group in groups
            for item in group
        )
    )


class CollectImplementationEvidenceUseCase:
    def __init__(
        self,
        repository_state_provider,
        test_state_provider,
        evidence_repository,
    ) -> None:
        self._repository_state_provider = (
            repository_state_provider
        )
        self._test_state_provider = test_state_provider
        self._evidence_repository = evidence_repository
        self._basis_builder = ImplementationEvidenceBasisBuilder()
        self._comparator = ImplementationEvidenceComparator()

    def execute(
        self,
        input_dto: CollectImplementationEvidenceInput,
    ) -> CollectImplementationEvidenceOutput:
        evidence_id = uuid4()

        def generation_failure(
            error_message: str,
        ) -> CollectImplementationEvidenceOutput:
            return CollectImplementationEvidenceOutput(
                success=False,
                evidence_id=evidence_id,
                implementation_id=input_dto.implementation_id,
                implementation_evidence=None,
                evidence_path=None,
                git_diff_path=None,
                status=None,
                missing_evidence=(),
                inconsistencies=(),
                human_approval_required=(),
                error_message=error_message,
            )

        implementation_kind = input_dto.implementation_kind
        previous_evidence_id = input_dto.previous_evidence_id

        if (
            implementation_kind == "INITIAL"
            and previous_evidence_id is not None
        ):
            return generation_failure(
                "INITIAL evidence must not have "
                "previous_evidence_id"
            )

        if (
            implementation_kind == "CORRECTION"
            and previous_evidence_id is None
        ):
            return generation_failure(
                "CORRECTION evidence requires "
                "previous_evidence_id"
            )

        if (
            implementation_kind == "REIMPLEMENTATION"
            and previous_evidence_id is None
        ):
            return generation_failure(
                "REIMPLEMENTATION evidence requires "
                "previous_evidence_id"
            )

        if previous_evidence_id == evidence_id:
            return generation_failure(
                "previous_evidence_id must not reference "
                "current evidence_id"
            )

        if (
            previous_evidence_id is not None
            and not self._evidence_repository.exists(
                previous_evidence_id
            )
        ):
            return generation_failure(
                "previous evidence does not exist: "
                f"{previous_evidence_id}"
            )

        try:
            repository_state = (
                self._repository_state_provider.get_state(
                    input_dto.base_commit
                )
            )
        except Exception as exc:
            return CollectImplementationEvidenceOutput(
                success=False,
                evidence_id=evidence_id,
                implementation_id=input_dto.implementation_id,
                implementation_evidence=None,
                evidence_path=None,
                git_diff_path=None,
                status=None,
                missing_evidence=(),
                inconsistencies=(),
                human_approval_required=(),
                error_message=(
                    "RepositoryStateProvider failed: "
                    f"{exc}"
                ),
            )

        try:
            test_state = self._test_state_provider.get_state()
        except Exception as exc:
            return CollectImplementationEvidenceOutput(
                success=False,
                evidence_id=evidence_id,
                implementation_id=input_dto.implementation_id,
                implementation_evidence=None,
                evidence_path=None,
                git_diff_path=None,
                status=None,
                missing_evidence=(),
                inconsistencies=(),
                human_approval_required=(),
                error_message=(
                    "TestStateProvider failed: "
                    f"{exc}"
                ),
            )

        basis_result = self._basis_builder.build(input_dto)

        comparison = self._comparator.compare(
            implementation_result=input_dto.implementation_result,
            repository_state=repository_state,
            test_state=test_state,
            scope=input_dto.approved_scope,
            expected_branch=input_dto.implementation_branch,
            expected_base_commit=input_dto.base_commit,
        )

        missing_evidence = _deduplicated(
            basis_result.missing_evidence,
            comparison.missing_evidence,
        )
        status = resolve_evidence_status(missing_evidence)

        basis_human_approval_required = tuple(
            "missing evidence requires human judgment: "
            f"{item}"
            for item in basis_result.missing_evidence
        )
        human_approval_required = _deduplicated(
            comparison.human_approval_required,
            basis_human_approval_required,
        )

        if "git_diff" in repository_state.unavailable_evidence:
            git_diff_path = None
        else:
            try:
                git_diff_path = (
                    self._evidence_repository.save_diff(
                        evidence_id,
                        repository_state.git_diff,
                    )
                )
            except Exception as exc:
                return CollectImplementationEvidenceOutput(
                    success=False,
                    evidence_id=evidence_id,
                    implementation_id=(
                        input_dto.implementation_id
                    ),
                    implementation_evidence=None,
                    evidence_path=None,
                    git_diff_path=None,
                    status=None,
                    missing_evidence=missing_evidence,
                    inconsistencies=(
                        comparison.inconsistencies
                    ),
                    human_approval_required=(
                        human_approval_required
                    ),
                    error_message=(
                        "Git Diff persistence failed: "
                        f"{exc}"
                    ),
                )

        implementation_result = input_dto.implementation_result

        if implementation_result is None:
            commands = ()
            unfinished_items = ()
            change_summary = None
        else:
            commands = _normalized_lines(
                implementation_result.executed_commands
            )
            unfinished_items = _normalized_optional_lines(
                implementation_result.incomplete_items
            )
            change_summary = (
                implementation_result.implementation_summary
            )

        verification_errors = _deduplicated(
            basis_result.errors,
            test_state.errors,
        )
        verification_warnings = _deduplicated(
            test_state.warnings,
        )

        evidence = ImplementationEvidence(
            identity=EvidenceIdentity(
                evidence_id=evidence_id,
                implementation_id=input_dto.implementation_id,
                implementation_kind=input_dto.implementation_kind,
                previous_evidence_id=(
                    input_dto.previous_evidence_id
                ),
                status=status,
                created_at=datetime.now().astimezone(),
            ),
            basis=basis_result.basis,
            scope=input_dto.approved_scope,
            changes=EvidenceChanges(
                created_files=repository_state.created_files,
                modified_files=repository_state.modified_files,
                deleted_files=repository_state.deleted_files,
                git_diff_path=git_diff_path,
                change_summary=change_summary,
            ),
            verification=EvidenceVerification(
                commands=commands,
                tests_created_or_modified=(
                    test_state.tests_created_or_modified
                ),
                test_commands=test_state.test_commands,
                initial_test_status=(
                    test_state.initial_test_status
                ),
                initial_test_result=(
                    test_state.initial_test_result
                ),
                target_test_status=(
                    test_state.target_test_status
                ),
                target_test_result=(
                    test_state.target_test_result
                ),
                full_test_status=test_state.full_test_status,
                full_test_result=test_state.full_test_result,
                errors=verification_errors,
                warnings=verification_warnings,
                no_tdd_reason=test_state.no_tdd_reason,
            ),
            deviations=EvidenceDeviations(
                out_of_scope_changes=(
                    comparison.out_of_scope_changes
                ),
                unplanned_changes=comparison.unplanned_changes,
                unfinished_items=unfinished_items,
                human_approval_required=(
                    human_approval_required
                ),
            ),
            codex_summary=EvidenceCodexSummary(
                implementation_result=implementation_result,
            ),
        )

        try:
            evidence_path = self._evidence_repository.save(
                evidence
            )
        except Exception as exc:
            return CollectImplementationEvidenceOutput(
                success=False,
                evidence_id=evidence_id,
                implementation_id=input_dto.implementation_id,
                implementation_evidence=evidence,
                evidence_path=None,
                git_diff_path=git_diff_path,
                status=status,
                missing_evidence=missing_evidence,
                inconsistencies=comparison.inconsistencies,
                human_approval_required=(
                    human_approval_required
                ),
                error_message=(
                    "Implementation Evidence persistence "
                    f"failed: {exc}"
                ),
            )

        return CollectImplementationEvidenceOutput(
            success=True,
            evidence_id=evidence_id,
            implementation_id=input_dto.implementation_id,
            implementation_evidence=evidence,
            evidence_path=evidence_path,
            git_diff_path=git_diff_path,
            status=status,
            missing_evidence=missing_evidence,
            inconsistencies=comparison.inconsistencies,
            human_approval_required=(
                human_approval_required
            ),
            error_message=None,
        )
