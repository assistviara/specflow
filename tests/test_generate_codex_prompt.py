from pathlib import Path

from application.dto import GenerateCodexPromptInput
from application.generate_codex_prompt import GenerateCodexPromptUseCase
from core.approval_record_service import (
    build_approval_record_from_artifact,
)


class FakeApprovalRecordRepository:
    def __init__(self, records: dict[str, dict]) -> None:
        self._records = records

    def get(self, approval_id: str) -> dict | None:
        return self._records.get(approval_id)


class FakePromptGenerator:
    def __init__(self) -> None:
        self.called = False

    def generate(self, **kwargs):
        self.called = True
        raise AssertionError(
            "Prompt generation must not start "
            "when approval is invalid."
        )


class FakeAIService:
    def run(self, request):
        raise AssertionError(
            "AI execution must not start "
            "when approval is invalid."
        )


def test_invalid_specification_approval_blocks_prompt_generation(
    tmp_path,
) -> None:
    specification_path = tmp_path / "specification.md"
    specification_path.write_text(
        "approved specification",
        encoding="utf-8",
    )

    implementation_plan_path = tmp_path / "implementation_plan.md"
    implementation_plan_path.write_text(
        "approved implementation plan",
        encoding="utf-8",
    )

    specification_record = build_approval_record_from_artifact(
        approval_id="spec-approval-001",
        artifact_type="specification",
        artifact_path=str(specification_path),
        decision="approved",
        approved_at="2026-09-09T10:00:00+09:00",
        comment="Specification approved.",
    )

    plan_record = build_approval_record_from_artifact(
        approval_id="plan-approval-001",
        artifact_type="implementation_plan",
        artifact_path=str(implementation_plan_path),
        decision="approved",
        approved_at="2026-09-09T10:01:00+09:00",
        comment="Implementation Plan approved.",
    )

    # Human Approval後にSpecificationが変更された状態を作る。
    specification_path.write_text(
        "modified specification",
        encoding="utf-8",
    )

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"status": "plan_approved"}',
        encoding="utf-8",
    )

    prompt_generator = FakePromptGenerator()

    use_case = GenerateCodexPromptUseCase(
        approval_repository=FakeApprovalRecordRepository(
            {
                "spec-approval-001": specification_record,
                "plan-approval-001": plan_record,
            }
        ),
        prompt_generator=prompt_generator,
        ai_service=FakeAIService(),
    )

    output = use_case.execute(
        GenerateCodexPromptInput(
            specification_path=specification_path,
            specification_approval_id="spec-approval-001",
            implementation_plan_path=implementation_plan_path,
            implementation_plan_approval_id="plan-approval-001",
            implementation_target_path=Path("application"),
            tdd_rules="Use TDD.",
            completion_conditions="Required tests pass.",
            stop_conditions=(
                "Stop when scope expansion is required."
            ),
            execution_result_reporting_requirements=(
                "Report changed files and test results."
            ),
            template_path=Path("implement_prompt_template.md"),
            state_file=state_file,
            state_history_dir=tmp_path / "state_history",
        )
    )

    assert (
        output.specification_approval_validation_result.is_valid
        is False
    )
    assert (
        "artifact hash does not match"
        in output.specification_approval_validation_result.validation_errors
    )
    assert (
        output.implementation_plan_approval_validation_result.is_valid
        is True
    )
    assert output.success is False
    assert output.prompt_usable is False
    assert output.codex_prompt is None
    assert output.current_state == "plan_approved"
    assert output.stop_reason is not None
    assert prompt_generator.called is False


def test_invalid_implementation_plan_approval_blocks_prompt_generation(
    tmp_path,
) -> None:
    specification_path = tmp_path / "specification.md"
    specification_path.write_text(
        "approved specification",
        encoding="utf-8",
    )

    implementation_plan_path = tmp_path / "implementation_plan.md"
    implementation_plan_path.write_text(
        "approved implementation plan",
        encoding="utf-8",
    )

    specification_record = build_approval_record_from_artifact(
        approval_id="spec-approval-001",
        artifact_type="specification",
        artifact_path=str(specification_path),
        decision="approved",
        approved_at="2026-09-09T10:00:00+09:00",
        comment="Specification approved.",
    )

    plan_record = build_approval_record_from_artifact(
        approval_id="plan-approval-001",
        artifact_type="implementation_plan",
        artifact_path=str(implementation_plan_path),
        decision="approved",
        approved_at="2026-09-09T10:01:00+09:00",
        comment="Implementation Plan approved.",
    )

    implementation_plan_path.write_text(
        "modified implementation plan",
        encoding="utf-8",
    )

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"status": "plan_approved"}',
        encoding="utf-8",
    )

    prompt_generator = FakePromptGenerator()

    use_case = GenerateCodexPromptUseCase(
        approval_repository=FakeApprovalRecordRepository(
            {
                "spec-approval-001": specification_record,
                "plan-approval-001": plan_record,
            }
        ),
        prompt_generator=prompt_generator,
        ai_service=FakeAIService(),
    )

    output = use_case.execute(
        GenerateCodexPromptInput(
            specification_path=specification_path,
            specification_approval_id="spec-approval-001",
            implementation_plan_path=implementation_plan_path,
            implementation_plan_approval_id="plan-approval-001",
            implementation_target_path=Path("application"),
            tdd_rules="Use TDD.",
            completion_conditions="Required tests pass.",
            stop_conditions=(
                "Stop when scope expansion is required."
            ),
            execution_result_reporting_requirements=(
                "Report changed files and test results."
            ),
            template_path=Path("implement_prompt_template.md"),
            state_file=state_file,
            state_history_dir=tmp_path / "state_history",
        )
    )

    assert (
        output.specification_approval_validation_result.is_valid
        is True
    )
    assert (
        output.implementation_plan_approval_validation_result.is_valid
        is False
    )
    assert (
        "artifact hash does not match"
        in output.implementation_plan_approval_validation_result.validation_errors
    )
    assert output.success is False
    assert output.prompt_usable is False
    assert output.codex_prompt is None
    assert output.current_state == "plan_approved"
    assert output.stop_reason is not None
    assert prompt_generator.called is False


def test_valid_approvals_move_to_implementation_prompt_generating(
    tmp_path,
) -> None:
    specification_path = tmp_path / "specification.md"
    specification_path.write_text(
        "approved specification",
        encoding="utf-8",
    )

    implementation_plan_path = tmp_path / "implementation_plan.md"
    implementation_plan_path.write_text(
        "approved implementation plan",
        encoding="utf-8",
    )

    specification_record = build_approval_record_from_artifact(
        approval_id="spec-approval-001",
        artifact_type="specification",
        artifact_path=str(specification_path),
        decision="approved",
        approved_at="2026-09-09T10:00:00+09:00",
        comment="Specification approved.",
    )

    plan_record = build_approval_record_from_artifact(
        approval_id="plan-approval-001",
        artifact_type="implementation_plan",
        artifact_path=str(implementation_plan_path),
        decision="approved",
        approved_at="2026-09-09T10:01:00+09:00",
        comment="Implementation Plan approved.",
    )

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"status": "plan_approved"}',
        encoding="utf-8",
    )

    class AllowedPromptGenerator:
        def generate(self, **kwargs):
            raise NotImplementedError(
                "stop after state transition"
            )

    use_case = GenerateCodexPromptUseCase(
        approval_repository=FakeApprovalRecordRepository(
            {
                "spec-approval-001": specification_record,
                "plan-approval-001": plan_record,
            }
        ),
        prompt_generator=AllowedPromptGenerator(),
        ai_service=FakeAIService(),
    )

    try:
        use_case.execute(
            GenerateCodexPromptInput(
                specification_path=specification_path,
                specification_approval_id="spec-approval-001",
                implementation_plan_path=implementation_plan_path,
                implementation_plan_approval_id="plan-approval-001",
                implementation_target_path=Path("application"),
                tdd_rules="Use TDD.",
                completion_conditions="Required tests pass.",
                stop_conditions=(
                    "Stop when scope expansion is required."
                ),
                execution_result_reporting_requirements=(
                    "Report changed files and test results."
                ),
                template_path=Path("implement_prompt_template.md"),
                state_file=state_file,
                state_history_dir=tmp_path / "state_history",
            )
        )
    except NotImplementedError:
        pass

    current_state = state_file.read_text(encoding="utf-8")

    assert (
        '"status": "implementation_prompt_generating"'
        in current_state
    )


def test_valid_approvals_call_prompt_generator(
    tmp_path,
) -> None:
    specification_path = tmp_path / "specification.md"
    specification_path.write_text(
        "approved specification",
        encoding="utf-8",
    )

    implementation_plan_path = tmp_path / "implementation_plan.md"
    implementation_plan_path.write_text(
        "approved implementation plan",
        encoding="utf-8",
    )

    specification_record = build_approval_record_from_artifact(
        approval_id="spec-approval-001",
        artifact_type="specification",
        artifact_path=str(specification_path),
        decision="approved",
        approved_at="2026-09-09T10:00:00+09:00",
        comment="Specification approved.",
    )

    plan_record = build_approval_record_from_artifact(
        approval_id="plan-approval-001",
        artifact_type="implementation_plan",
        artifact_path=str(implementation_plan_path),
        decision="approved",
        approved_at="2026-09-09T10:01:00+09:00",
        comment="Implementation Plan approved.",
    )

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"status": "plan_approved"}',
        encoding="utf-8",
    )

    class RecordingPromptGenerator:
        def __init__(self) -> None:
            self.called = False
            self.kwargs = None

        def generate(self, **kwargs):
            self.called = True
            self.kwargs = kwargs
            raise RuntimeError("stop after prompt generation")

    prompt_generator = RecordingPromptGenerator()

    use_case = GenerateCodexPromptUseCase(
        approval_repository=FakeApprovalRecordRepository(
            {
                "spec-approval-001": specification_record,
                "plan-approval-001": plan_record,
            }
        ),
        prompt_generator=prompt_generator,
        ai_service=FakeAIService(),
    )

    try:
        use_case.execute(
            GenerateCodexPromptInput(
                specification_path=specification_path,
                specification_approval_id="spec-approval-001",
                implementation_plan_path=implementation_plan_path,
                implementation_plan_approval_id="plan-approval-001",
                implementation_target_path=Path("application"),
                tdd_rules="Use TDD.",
                completion_conditions="Required tests pass.",
                stop_conditions=(
                    "Stop when scope expansion is required."
                ),
                execution_result_reporting_requirements=(
                    "Report changed files and test results."
                ),
                template_path=Path("implement_prompt_template.md"),
                state_file=state_file,
                state_history_dir=tmp_path / "state_history",
            )
        )
    except RuntimeError as exc:
        assert str(exc) == "stop after prompt generation"

    assert prompt_generator.called is True
    assert prompt_generator.kwargs == {
        "specification_path": specification_path,
        "implementation_plan_path": implementation_plan_path,
        "implementation_target_path": Path("application"),
        "tdd_rules": "Use TDD.",
        "completion_conditions": "Required tests pass.",
        "stop_conditions": (
            "Stop when scope expansion is required."
        ),
        "execution_result_reporting_requirements": (
            "Report changed files and test results."
        ),
        "template_path": Path("implement_prompt_template.md"),
    }


def test_generated_prompt_is_sent_to_ai_service(
    tmp_path,
) -> None:
    from core.ai.ai_response import AIResponse
    from core.prompt_builder import PromptResult

    specification_path = tmp_path / "specification.md"
    specification_path.write_text(
        "approved specification",
        encoding="utf-8",
    )

    implementation_plan_path = tmp_path / "implementation_plan.md"
    implementation_plan_path.write_text(
        "approved implementation plan",
        encoding="utf-8",
    )

    specification_record = build_approval_record_from_artifact(
        approval_id="spec-approval-001",
        artifact_type="specification",
        artifact_path=str(specification_path),
        decision="approved",
        approved_at="2026-09-09T10:00:00+09:00",
        comment="Specification approved.",
    )

    plan_record = build_approval_record_from_artifact(
        approval_id="plan-approval-001",
        artifact_type="implementation_plan",
        artifact_path=str(implementation_plan_path),
        decision="approved",
        approved_at="2026-09-09T10:01:00+09:00",
        comment="Implementation Plan approved.",
    )

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"status": "plan_approved"}',
        encoding="utf-8",
    )

    class ReturningPromptGenerator:
        def generate(self, **kwargs):
            return PromptResult(
                content="PROMPT FOR CHATGPT",
                undefined_variables=[],
                unused_context=[],
                warnings=[],
            )

    class RecordingAIService:
        def __init__(self) -> None:
            self.request = None

        def run(self, request):
            self.request = request
            return AIResponse(
                content="AI RESPONSE",
                success=True,
                error_message=None,
            )

    ai_service = RecordingAIService()

    use_case = GenerateCodexPromptUseCase(
        approval_repository=FakeApprovalRecordRepository(
            {
                "spec-approval-001": specification_record,
                "plan-approval-001": plan_record,
            }
        ),
        prompt_generator=ReturningPromptGenerator(),
        ai_service=ai_service,
    )

    try:
        use_case.execute(
            GenerateCodexPromptInput(
                specification_path=specification_path,
                specification_approval_id="spec-approval-001",
                implementation_plan_path=implementation_plan_path,
                implementation_plan_approval_id="plan-approval-001",
                implementation_target_path=Path("application"),
                tdd_rules="Use TDD.",
                completion_conditions="Required tests pass.",
                stop_conditions=(
                    "Stop when scope expansion is required."
                ),
                execution_result_reporting_requirements=(
                    "Report changed files and test results."
                ),
                template_path=Path("implement_prompt_template.md"),
                state_file=state_file,
                state_history_dir=tmp_path / "state_history",
            )
        )
    except NotImplementedError:
        pass

    assert ai_service.request is not None
    assert ai_service.request.prompt == "PROMPT FOR CHATGPT"


def test_ai_failure_does_not_move_to_implementation_ready(
    tmp_path,
) -> None:
    from core.ai.ai_response import AIResponse
    from core.prompt_builder import PromptResult

    specification_path = tmp_path / "specification.md"
    specification_path.write_text(
        "approved specification",
        encoding="utf-8",
    )

    implementation_plan_path = tmp_path / "implementation_plan.md"
    implementation_plan_path.write_text(
        "approved implementation plan",
        encoding="utf-8",
    )

    specification_record = build_approval_record_from_artifact(
        approval_id="spec-approval-001",
        artifact_type="specification",
        artifact_path=str(specification_path),
        decision="approved",
        approved_at="2026-09-09T10:00:00+09:00",
        comment="Specification approved.",
    )

    plan_record = build_approval_record_from_artifact(
        approval_id="plan-approval-001",
        artifact_type="implementation_plan",
        artifact_path=str(implementation_plan_path),
        decision="approved",
        approved_at="2026-09-09T10:01:00+09:00",
        comment="Implementation Plan approved.",
    )

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"status": "plan_approved"}',
        encoding="utf-8",
    )

    class ReturningPromptGenerator:
        def generate(self, **kwargs):
            return PromptResult(
                content="PROMPT FOR CHATGPT",
                undefined_variables=[],
                unused_context=[],
                warnings=[],
            )

    class FailingAIService:
        def run(self, request):
            return AIResponse(
                content="",
                success=False,
                error_message="AI generation failed",
            )

    use_case = GenerateCodexPromptUseCase(
        approval_repository=FakeApprovalRecordRepository(
            {
                "spec-approval-001": specification_record,
                "plan-approval-001": plan_record,
            }
        ),
        prompt_generator=ReturningPromptGenerator(),
        ai_service=FailingAIService(),
    )

    output = use_case.execute(
        GenerateCodexPromptInput(
            specification_path=specification_path,
            specification_approval_id="spec-approval-001",
            implementation_plan_path=implementation_plan_path,
            implementation_plan_approval_id="plan-approval-001",
            implementation_target_path=Path("application"),
            tdd_rules="Use TDD.",
            completion_conditions="Required tests pass.",
            stop_conditions=(
                "Stop when scope expansion is required."
            ),
            execution_result_reporting_requirements=(
                "Report changed files and test results."
            ),
            template_path=Path("implement_prompt_template.md"),
            state_file=state_file,
            state_history_dir=tmp_path / "state_history",
        )
    )

    assert output.success is False
    assert output.codex_prompt is None
    assert output.prompt_usable is False
    assert output.current_state == "implementation_prompt_generating"
    assert output.stop_reason == "AI generation failed"
    assert output.error_message == "AI generation failed"

    current_state = state_file.read_text(encoding="utf-8")
    assert (
        '"status": "implementation_prompt_generating"'
        in current_state
    )


def test_unusable_ai_output_does_not_move_to_implementation_ready(
    tmp_path,
) -> None:
    from core.ai.ai_response import AIResponse
    from core.prompt_builder import PromptResult

    specification_path = tmp_path / "specification.md"
    specification_path.write_text(
        "approved specification",
        encoding="utf-8",
    )

    implementation_plan_path = tmp_path / "implementation_plan.md"
    implementation_plan_path.write_text(
        "approved implementation plan",
        encoding="utf-8",
    )

    specification_record = build_approval_record_from_artifact(
        approval_id="spec-approval-001",
        artifact_type="specification",
        artifact_path=str(specification_path),
        decision="approved",
        approved_at="2026-09-09T10:00:00+09:00",
        comment="Specification approved.",
    )

    plan_record = build_approval_record_from_artifact(
        approval_id="plan-approval-001",
        artifact_type="implementation_plan",
        artifact_path=str(implementation_plan_path),
        decision="approved",
        approved_at="2026-09-09T10:01:00+09:00",
        comment="Implementation Plan approved.",
    )

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"status": "plan_approved"}',
        encoding="utf-8",
    )

    class ReturningPromptGenerator:
        def generate(self, **kwargs):
            return PromptResult(
                content="PROMPT FOR CHATGPT",
                undefined_variables=[],
                unused_context=[],
                warnings=[],
            )

    class SuccessfulButInvalidAIService:
        def run(self, request):
            return AIResponse(
                content="""## Implementation Scope
scope

## Allowed Changes
allowed
""",
                success=True,
                error_message=None,
            )

    use_case = GenerateCodexPromptUseCase(
        approval_repository=FakeApprovalRecordRepository(
            {
                "spec-approval-001": specification_record,
                "plan-approval-001": plan_record,
            }
        ),
        prompt_generator=ReturningPromptGenerator(),
        ai_service=SuccessfulButInvalidAIService(),
    )

    output = use_case.execute(
        GenerateCodexPromptInput(
            specification_path=specification_path,
            specification_approval_id="spec-approval-001",
            implementation_plan_path=implementation_plan_path,
            implementation_plan_approval_id="plan-approval-001",
            implementation_target_path=Path("application"),
            tdd_rules="Use TDD.",
            completion_conditions="Required tests pass.",
            stop_conditions=(
                "Stop when scope expansion is required."
            ),
            execution_result_reporting_requirements=(
                "Report changed files and test results."
            ),
            template_path=Path("implement_prompt_template.md"),
            state_file=state_file,
            state_history_dir=tmp_path / "state_history",
        )
    )

    assert output.success is False
    assert output.codex_prompt is None
    assert output.prompt_usable is False
    assert output.current_state == "implementation_prompt_generating"
    assert output.stop_reason == "required section is missing"
    assert output.error_message == "required section is missing"

    current_state = state_file.read_text(encoding="utf-8")
    assert (
        '"status": "implementation_prompt_generating"'
        in current_state
    )


def test_usable_codex_prompt_moves_to_implementation_ready(
    tmp_path,
) -> None:
    from core.ai.ai_response import AIResponse
    from core.prompt_builder import PromptResult

    specification_path = tmp_path / "specification.md"
    specification_path.write_text(
        "approved specification",
        encoding="utf-8",
    )

    implementation_plan_path = tmp_path / "implementation_plan.md"
    implementation_plan_path.write_text(
        "approved implementation plan",
        encoding="utf-8",
    )

    specification_record = build_approval_record_from_artifact(
        approval_id="spec-approval-001",
        artifact_type="specification",
        artifact_path=str(specification_path),
        decision="approved",
        approved_at="2026-09-09T10:00:00+09:00",
        comment="Specification approved.",
    )

    plan_record = build_approval_record_from_artifact(
        approval_id="plan-approval-001",
        artifact_type="implementation_plan",
        artifact_path=str(implementation_plan_path),
        decision="approved",
        approved_at="2026-09-09T10:01:00+09:00",
        comment="Implementation Plan approved.",
    )

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"status": "plan_approved"}',
        encoding="utf-8",
    )

    codex_prompt = """## Implementation Scope
Implement only the approved scope.

## Allowed Changes
Change files within the approved implementation target.

## Forbidden Changes
Do not change files outside the approved scope.

## TDD Requirements
Use RED, GREEN, and regression testing.

## Completion Conditions
Required tests pass.

## Stop Conditions
Stop when scope expansion is required.

## Required Execution Result Reporting
Report changed files, commands, and test results.

## Human Approval Required Conditions
Request Human Approval before changes beyond approved scope.
"""

    class ReturningPromptGenerator:
        def generate(self, **kwargs):
            return PromptResult(
                content="PROMPT FOR CHATGPT",
                undefined_variables=[],
                unused_context=[],
                warnings=[],
            )

    class SuccessfulAIService:
        def run(self, request):
            return AIResponse(
                content=codex_prompt,
                success=True,
                error_message=None,
            )

    use_case = GenerateCodexPromptUseCase(
        approval_repository=FakeApprovalRecordRepository(
            {
                "spec-approval-001": specification_record,
                "plan-approval-001": plan_record,
            }
        ),
        prompt_generator=ReturningPromptGenerator(),
        ai_service=SuccessfulAIService(),
    )

    output = use_case.execute(
        GenerateCodexPromptInput(
            specification_path=specification_path,
            specification_approval_id="spec-approval-001",
            implementation_plan_path=implementation_plan_path,
            implementation_plan_approval_id="plan-approval-001",
            implementation_target_path=Path("application"),
            tdd_rules="Use TDD.",
            completion_conditions="Required tests pass.",
            stop_conditions=(
                "Stop when scope expansion is required."
            ),
            execution_result_reporting_requirements=(
                "Report changed files and test results."
            ),
            template_path=Path("implement_prompt_template.md"),
            state_file=state_file,
            state_history_dir=tmp_path / "state_history",
        )
    )

    assert output.success is True
    assert output.codex_prompt == codex_prompt
    assert output.prompt_usable is True
    assert output.current_state == "implementation_ready"
    assert output.stop_reason is None
    assert output.error_message is None

    assert (
        output.specification_approval_validation_result.is_valid
        is True
    )
    assert (
        output.implementation_plan_approval_validation_result.is_valid
        is True
    )

    current_state = state_file.read_text(encoding="utf-8")
    assert '"status": "implementation_ready"' in current_state


def test_unready_prompt_result_does_not_move_to_implementation_ready(
    tmp_path,
) -> None:
    from core.prompt_builder import PromptResult

    specification_path = tmp_path / "specification.md"
    specification_path.write_text(
        "approved specification",
        encoding="utf-8",
    )

    implementation_plan_path = tmp_path / "implementation_plan.md"
    implementation_plan_path.write_text(
        "approved implementation plan",
        encoding="utf-8",
    )

    specification_record = build_approval_record_from_artifact(
        approval_id="spec-approval-001",
        artifact_type="specification",
        artifact_path=str(specification_path),
        decision="approved",
        approved_at="2026-09-09T10:00:00+09:00",
        comment="Specification approved.",
    )

    plan_record = build_approval_record_from_artifact(
        approval_id="plan-approval-001",
        artifact_type="implementation_plan",
        artifact_path=str(implementation_plan_path),
        decision="approved",
        approved_at="2026-09-09T10:01:00+09:00",
        comment="Implementation Plan approved.",
    )

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"status": "plan_approved"}',
        encoding="utf-8",
    )

    class UnreadyPromptGenerator:
        def generate(self, **kwargs):
            return PromptResult(
                content="",
                undefined_variables=["SPECIFICATION"],
                unused_context=[],
                warnings=[],
            )

    class AIServiceMustNotRun:
        def run(self, request):
            raise AssertionError(
                "AIService must not run for an unready PromptResult."
            )

    use_case = GenerateCodexPromptUseCase(
        approval_repository=FakeApprovalRecordRepository(
            {
                "spec-approval-001": specification_record,
                "plan-approval-001": plan_record,
            }
        ),
        prompt_generator=UnreadyPromptGenerator(),
        ai_service=AIServiceMustNotRun(),
    )

    output = use_case.execute(
        GenerateCodexPromptInput(
            specification_path=specification_path,
            specification_approval_id="spec-approval-001",
            implementation_plan_path=implementation_plan_path,
            implementation_plan_approval_id="plan-approval-001",
            implementation_target_path=Path("application"),
            tdd_rules="Use TDD.",
            completion_conditions="Required tests pass.",
            stop_conditions=(
                "Stop when scope expansion is required."
            ),
            execution_result_reporting_requirements=(
                "Report changed files and test results."
            ),
            template_path=Path("implement_prompt_template.md"),
            state_file=state_file,
            state_history_dir=tmp_path / "state_history",
        )
    )

    assert output.success is False
    assert output.codex_prompt is None
    assert output.prompt_usable is False
    assert output.current_state == "implementation_prompt_generating"
    assert (
        output.stop_reason
        == "PromptResult is not ready for AI execution."
    )
    assert (
        output.error_message
        == "PromptResult is not ready for AI execution."
    )

    current_state = state_file.read_text(encoding="utf-8")
    assert '"status": "implementation_prompt_generating"' in current_state
