from datetime import datetime
from uuid import uuid4

from application.current_state_repository import load_current_state
from application.dto import (
    GenerateCodexPromptInput,
    GenerateCodexPromptOutput,
)
from application.state_transition import transition_state
from application.codex_prompt_output_parser import (
    CodexPromptOutputParseError,
    parse_codex_prompt_output,
)
from core.approval_validation import validate_approval_result
from core.ai.prompt_adapter import PromptAdapter


_IMPLEMENTATION_REPORT_FORMAT = """### Mandatory final report format

For your final implementation response, use all ten headings below exactly once,
in this order, with nonempty bodies. Replace every angle-bracket placeholder with
observed facts; do not return placeholders or wrap the final report in a code fence.
This is a reporting format, not an instruction to perform additional work.
Preserve all approved scope, TDD, STOP and Human Approval requirements above.
Do not fabricate changes, commands, test results, completion, or approval.
Even when execution is blocked or stopped, report what actually happened and list
unfinished work under Incomplete Items and any needed decision under Human Approval Required.

TEST_REQUIRED must be YES or NO according to the approved test requirements,
not according to whether tests happened to run. Do not infer an exemption.
Test Execution Status must contain only COMPLETED, ERROR, or NOT_RUN.
Test Result must contain only PASS, FAIL, or NONE. Use NOT_RUN / NONE when tests
were not run; report execution errors as ERROR, and do not claim PASS without evidence.
Put explanations in the other sections, not after these single-value fields.
In Test Execution Error, include both metadata lines exactly as shown, without
indentation or bullet prefixes. TECHNICAL_RETRY_SAFE is YES, NO, or UNKNOWN.
Use UNKNOWN when safety is unverified. For NO or UNKNOWN, TECHNICAL_RETRY_OPERATION
must be NONE; for YES, name the specific safely repeatable technical operation,
not NONE. This report is not authorization to retry or to bypass Human Approval.
For free-text sections, use NONE only when genuinely absent; otherwise describe
the facts, uncertainty, remaining work, or required Human decision. Never use NONE
to conceal unfinished work. A parsed report is not proof of successful implementation.

```text
## Implementation Summary
TEST_REQUIRED: <test_required>
<summary>
## Changed Files
<changed_files>
## Executed Commands
<executed_commands>
## Test Execution Status
<test_status>
## Test Result
<test_result>
## Test Execution Error
TECHNICAL_RETRY_SAFE: <retry_safe>
TECHNICAL_RETRY_OPERATION: <retry_operation>
<test_error>
## Errors
<errors>
## Warnings
<warnings>
## Incomplete Items
<incomplete_items>
## Human Approval Required
<human_approval>
```

"""


class GenerateCodexPromptUseCase:
    def __init__(
        self,
        approval_repository,
        prompt_generator,
        ai_service,
    ) -> None:
        self._approval_repository = approval_repository
        self._prompt_generator = prompt_generator
        self._ai_service = ai_service

    def execute(
        self,
        input_dto: GenerateCodexPromptInput,
    ) -> GenerateCodexPromptOutput:
        specification_record = self._approval_repository.get(
            input_dto.specification_approval_id
        )
        implementation_plan_record = self._approval_repository.get(
            input_dto.implementation_plan_approval_id
        )

        specification_validation = validate_approval_result(
            specification_record,
            str(input_dto.specification_path),
            "specification",
        )
        implementation_plan_validation = validate_approval_result(
            implementation_plan_record,
            str(input_dto.implementation_plan_path),
            "implementation_plan",
        )

        current_state = load_current_state(
            input_dto.state_file
        )["status"]

        if (
            not specification_validation.is_valid
            or not implementation_plan_validation.is_valid
        ):
            return GenerateCodexPromptOutput(
                success=False,
                codex_prompt=None,
                specification_path=input_dto.specification_path,
                implementation_plan_path=(
                    input_dto.implementation_plan_path
                ),
                specification_approval_validation_result=(
                    specification_validation
                ),
                implementation_plan_approval_validation_result=(
                    implementation_plan_validation
                ),
                prompt_usable=False,
                current_state=current_state,
                stop_reason="Approval validation failed.",
            )

        transition_state(
            input_dto.state_file,
            input_dto.state_history_dir,
            {
                "transition_id": str(uuid4()),
                "from_state": current_state,
                "to_state": "implementation_prompt_generating",
                "occurred_at": datetime.now().astimezone().isoformat(),
                "reason": "Codex Implementation Prompt generation started",
            },
        )

        prompt_result = self._prompt_generator.generate(
            specification_path=input_dto.specification_path,
            implementation_plan_path=input_dto.implementation_plan_path,
            implementation_target_path=(
                input_dto.implementation_target_path
            ),
            tdd_rules=input_dto.tdd_rules,
            completion_conditions=input_dto.completion_conditions,
            stop_conditions=input_dto.stop_conditions,
            execution_result_reporting_requirements=(
                input_dto.execution_result_reporting_requirements
            ),
            template_path=input_dto.template_path,
        )

        try:
            ai_request = PromptAdapter.to_ai_request(
                prompt_result
            )
        except ValueError as exc:
            current_state = load_current_state(
                input_dto.state_file
            )["status"]

            return GenerateCodexPromptOutput(
                success=False,
                codex_prompt=None,
                specification_path=input_dto.specification_path,
                implementation_plan_path=(
                    input_dto.implementation_plan_path
                ),
                specification_approval_validation_result=(
                    specification_validation
                ),
                implementation_plan_approval_validation_result=(
                    implementation_plan_validation
                ),
                prompt_usable=False,
                current_state=current_state,
                stop_reason=str(exc),
                error_message=str(exc),
            )

        ai_response = self._ai_service.run(
            ai_request
        )

        if not ai_response.success:
            current_state = load_current_state(
                input_dto.state_file
            )["status"]

            return GenerateCodexPromptOutput(
                success=False,
                codex_prompt=None,
                specification_path=input_dto.specification_path,
                implementation_plan_path=(
                    input_dto.implementation_plan_path
                ),
                specification_approval_validation_result=(
                    specification_validation
                ),
                implementation_plan_approval_validation_result=(
                    implementation_plan_validation
                ),
                prompt_usable=False,
                current_state=current_state,
                stop_reason=ai_response.error_message,
                error_message=ai_response.error_message,
            )

        try:
            parse_codex_prompt_output(
                ai_response.content
            )
        except CodexPromptOutputParseError as exc:
            current_state = load_current_state(
                input_dto.state_file
            )["status"]

            return GenerateCodexPromptOutput(
                success=False,
                codex_prompt=None,
                specification_path=input_dto.specification_path,
                implementation_plan_path=(
                    input_dto.implementation_plan_path
                ),
                specification_approval_validation_result=(
                    specification_validation
                ),
                implementation_plan_approval_validation_result=(
                    implementation_plan_validation
                ),
                prompt_usable=False,
                current_state=current_state,
                stop_reason=str(exc),
                error_message=str(exc),
            )

        current_state = load_current_state(
            input_dto.state_file
        )["status"]

        transition_state(
            input_dto.state_file,
            input_dto.state_history_dir,
            {
                "transition_id": str(uuid4()),
                "from_state": current_state,
                "to_state": "implementation_ready",
                "occurred_at": datetime.now().astimezone().isoformat(),
                "reason": "Codex Implementation Prompt generated",
            },
        )

        # Supply the parser contract deterministically; do not rely on AI to
        # reproduce it. The generated scope and Human decision text stay intact.
        reporting_end = ai_response.content.index("## Human Approval Required Conditions")
        codex_prompt = (ai_response.content[:reporting_end]
                        + _IMPLEMENTATION_REPORT_FORMAT
                        + ai_response.content[reporting_end:])

        return GenerateCodexPromptOutput(
            success=True,
            codex_prompt=codex_prompt,
            specification_path=input_dto.specification_path,
            implementation_plan_path=(
                input_dto.implementation_plan_path
            ),
            specification_approval_validation_result=(
                specification_validation
            ),
            implementation_plan_approval_validation_result=(
                implementation_plan_validation
            ),
            prompt_usable=True,
            current_state="implementation_ready",
        )
