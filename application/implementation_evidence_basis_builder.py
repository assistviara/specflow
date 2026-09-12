import hashlib
from dataclasses import dataclass

from application.dto import CollectImplementationEvidenceInput
from application.implementation_evidence import EvidenceBasis


@dataclass(frozen=True)
class EvidenceBasisBuildResult:
    basis: EvidenceBasis
    missing_evidence: tuple[str, ...]
    errors: tuple[str, ...]


class ImplementationEvidenceBasisBuilder:
    def build(
        self,
        input_dto: CollectImplementationEvidenceInput,
    ) -> EvidenceBasisBuildResult:
        missing_evidence: list[str] = []
        errors: list[str] = []

        try:
            specification_hash = hashlib.sha256(
                input_dto.specification_path.read_bytes()
            ).hexdigest()
        except OSError:
            specification_hash = None
            missing_evidence.append(
                "specification hash unavailable"
            )
            errors.append(
                "failed to read specification for hashing"
            )

        try:
            implementation_plan_hash = hashlib.sha256(
                input_dto.implementation_plan_path.read_bytes()
            ).hexdigest()
        except OSError:
            implementation_plan_hash = None
            missing_evidence.append(
                "implementation plan hash unavailable"
            )
            errors.append(
                "failed to read implementation plan for hashing"
            )

        codex_prompt_hash = hashlib.sha256(
            input_dto.codex_prompt.encode("utf-8")
        ).hexdigest()

        basis = EvidenceBasis(
            specification_path=input_dto.specification_path,
            specification_hash=specification_hash,
            specification_approval_id=(
                input_dto.specification_approval_id
            ),
            implementation_plan_path=(
                input_dto.implementation_plan_path
            ),
            implementation_plan_hash=implementation_plan_hash,
            implementation_plan_approval_id=(
                input_dto.implementation_plan_approval_id
            ),
            codex_prompt_path=input_dto.codex_prompt_path,
            codex_prompt_hash=codex_prompt_hash,
        )

        return EvidenceBasisBuildResult(
            basis=basis,
            missing_evidence=tuple(missing_evidence),
            errors=tuple(errors),
        )
