import hashlib

from application.dto import CollectImplementationEvidenceInput
from application.implementation_evidence import EvidenceBasis


class ImplementationEvidenceBasisBuilder:
    def build(
        self,
        input_dto: CollectImplementationEvidenceInput,
    ) -> EvidenceBasis:
        specification_hash = hashlib.sha256(
            input_dto.specification_path.read_bytes()
        ).hexdigest()

        implementation_plan_hash = hashlib.sha256(
            input_dto.implementation_plan_path.read_bytes()
        ).hexdigest()

        codex_prompt_hash = hashlib.sha256(
            input_dto.codex_prompt.encode("utf-8")
        ).hexdigest()

        return EvidenceBasis(
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
