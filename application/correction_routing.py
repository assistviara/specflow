from dataclasses import dataclass
from enum import Enum

from application.review_result import ReviewResultOutput
from application.review_retry import ReviewRetryHistory


class ReturnDestination(str, Enum):
    SPECIFICATION = 'Specification策定工程'
    PLAN = 'Plan修正工程'
    PROMPT = 'Prompt再生成工程'
    IMPLEMENTATION = 'Codex再実装工程'
    TEST = 'Test修正工程'
    HUMAN = 'Human判断'
    CRITICAL_APPROVAL = 'Critical Change Approval工程'


@dataclass(frozen=True)
class RoutingControl:
    correction_allowed: bool | None
    correction_count: int | None
    early_stop_triggered: bool | None
    count_condition_met: bool | None


@dataclass(frozen=True)
class CorrectionProblem:
    destination: str | None
    targets: tuple[str, ...]
    finding_references: tuple[str, ...]
    scope_reference: str
    safe_in_scope: bool
    safe_scope_reason: str
    required_test_references: tuple[str, ...]
    correction_references: tuple[str, ...]
    # Caller confirmation of safe joint correction, not an AI-selected grouping.
    safe_group: str | None = None


@dataclass(frozen=True)
class CorrectionRoutingInput:
    review: ReviewResultOutput
    problems: tuple[CorrectionProblem, ...]
    current_state: str | None
    control: RoutingControl
    retry_history: tuple[ReviewRetryHistory, ...] = ()


@dataclass(frozen=True)
class CorrectionInstruction:
    destination: str
    problem: str
    cause: str
    targets: tuple[str, ...]
    rationale: str
    review_reference: str
    finding_references: tuple[str, ...]
    basis_references: tuple[str, ...]
    scope_reference: str
    allowed_changes: tuple[str, ...]
    forbidden_changes: tuple[str, ...]
    safe_scope_reasons: tuple[str, ...]
    required_test_references: tuple[str, ...]
    correction_references: tuple[str, ...]


@dataclass(frozen=True)
class CorrectionRoutingOutput:
    request: CorrectionRoutingInput
    instructions: tuple[CorrectionInstruction, ...] = ()
    blocked_reasons: tuple[str, ...] = ()
    execution_error: str | None = None
    parse_error: str | None = None
    validation_errors: tuple[str, ...] = ()
    raw_response: str | None = None

    @property
    def ready(self) -> bool:
        return bool(self.instructions) and not (
            self.blocked_reasons or self.execution_error or self.parse_error or self.validation_errors
        )
