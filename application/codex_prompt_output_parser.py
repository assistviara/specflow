from dataclasses import dataclass


@dataclass(frozen=True)
class CodexPromptOutput:
    implementation_scope: str
    allowed_changes: str
    forbidden_changes: str
    tdd_requirements: str
    completion_conditions: str
    stop_conditions: str
    required_execution_result_reporting: str
    human_approval_required_conditions: str


class CodexPromptOutputParseError(ValueError):
    pass


_REQUIRED_HEADINGS = [
    "## Implementation Scope",
    "## Allowed Changes",
    "## Forbidden Changes",
    "## TDD Requirements",
    "## Completion Conditions",
    "## Stop Conditions",
    "## Required Execution Result Reporting",
    "## Human Approval Required Conditions",
]


def parse_codex_prompt_output(content: str) -> CodexPromptOutput:
    try:
        positions = [
            content.index(heading)
            for heading in _REQUIRED_HEADINGS
        ]
    except ValueError as exc:
        raise CodexPromptOutputParseError(
            "required section is missing"
        ) from exc

    if positions != sorted(positions):
        raise CodexPromptOutputParseError(
            "sections are out of order"
        )

    sections: list[str] = []

    for index, heading in enumerate(_REQUIRED_HEADINGS):
        start = positions[index] + len(heading)

        if index + 1 < len(_REQUIRED_HEADINGS):
            end = positions[index + 1]
        else:
            end = len(content)

        sections.append(
            content[start:end].strip()
        )

    if any(not section for section in sections):
        raise CodexPromptOutputParseError(
            "required section is empty"
        )

    return CodexPromptOutput(
        implementation_scope=sections[0],
        allowed_changes=sections[1],
        forbidden_changes=sections[2],
        tdd_requirements=sections[3],
        completion_conditions=sections[4],
        stop_conditions=sections[5],
        required_execution_result_reporting=sections[6],
        human_approval_required_conditions=sections[7],
    )
