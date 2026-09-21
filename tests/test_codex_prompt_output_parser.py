from application.codex_prompt_output_parser import (
    CodexPromptOutputParseError,
    parse_codex_prompt_output,
)


VALID_CONTENT = """## Implementation Scope
scope

## Allowed Changes
allowed

## Forbidden Changes
forbidden

## TDD Requirements
Use these Test phase wrappers:

python -m infrastructure.specflow_test_wrapper --phase initial -- pytest
python -m infrastructure.specflow_test_wrapper --phase target -- pytest
python -m infrastructure.specflow_test_wrapper --phase full -- pytest

## Completion Conditions
complete

## Stop Conditions
stop

## Required Execution Result Reporting
report

## Human Approval Required Conditions
approval
"""


def test_parse_codex_prompt_output_returns_sections() -> None:
    result = parse_codex_prompt_output(VALID_CONTENT)

    assert result.implementation_scope == "scope"
    assert result.allowed_changes == "allowed"
    assert result.forbidden_changes == "forbidden"
    assert (
        "infrastructure.specflow_test_wrapper "
        "--phase initial --"
        in result.tdd_requirements
    )
    assert (
        "infrastructure.specflow_test_wrapper "
        "--phase target --"
        in result.tdd_requirements
    )
    assert (
        "infrastructure.specflow_test_wrapper "
        "--phase full --"
        in result.tdd_requirements
    )
    assert result.completion_conditions == "complete"
    assert result.stop_conditions == "stop"
    assert result.required_execution_result_reporting == "report"
    assert result.human_approval_required_conditions == "approval"


def test_parse_codex_prompt_output_raises_when_required_section_missing() -> None:
    invalid_content = """## Implementation Scope
scope

## Allowed Changes
allowed

## Forbidden Changes
forbidden

## TDD Requirements
tdd

## Completion Conditions
complete

## Stop Conditions
stop

## Required Execution Result Reporting
report
"""

    try:
        parse_codex_prompt_output(invalid_content)
    except CodexPromptOutputParseError as exc:
        assert str(exc) == "required section is missing"
    else:
        raise AssertionError(
            "CodexPromptOutputParseError was not raised"
        )


def test_parse_codex_prompt_output_raises_when_sections_out_of_order() -> None:
    invalid_content = """## Allowed Changes
allowed

## Implementation Scope
scope

## Forbidden Changes
forbidden

## TDD Requirements
tdd

## Completion Conditions
complete

## Stop Conditions
stop

## Required Execution Result Reporting
report

## Human Approval Required Conditions
approval
"""

    try:
        parse_codex_prompt_output(invalid_content)
    except CodexPromptOutputParseError as exc:
        assert str(exc) == "sections are out of order"
    else:
        raise AssertionError(
            "CodexPromptOutputParseError was not raised"
        )


def test_parse_codex_prompt_output_raises_when_required_section_empty() -> None:
    invalid_content = """## Implementation Scope

## Allowed Changes
allowed

## Forbidden Changes
forbidden

## TDD Requirements
tdd

## Completion Conditions
complete

## Stop Conditions
stop

## Required Execution Result Reporting
report

## Human Approval Required Conditions
approval
"""

    try:
        parse_codex_prompt_output(invalid_content)
    except CodexPromptOutputParseError as exc:
        assert str(exc) == "required section is empty"
    else:
        raise AssertionError(
            "CodexPromptOutputParseError was not raised"
        )



def test_parse_rejects_tdd_requirements_without_phase_wrappers():
    invalid_content = """## Implementation Scope
scope

## Allowed Changes
allowed

## Forbidden Changes
forbidden

## TDD Requirements
Use TDD, but run tests directly.

## Completion Conditions
complete

## Stop Conditions
stop

## Required Execution Result Reporting
report

## Human Approval Required Conditions
approval
"""

    try:
        parse_codex_prompt_output(
            invalid_content
        )
    except CodexPromptOutputParseError as exc:
        assert str(exc) == (
            "required Test phase wrapper "
            "instruction is missing"
        )
    else:
        raise AssertionError(
            "CodexPromptOutputParseError was not raised"
        )
