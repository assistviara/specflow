from pathlib import Path


def test_implement_prompt_template_contains_required_generation_constraints():
    template_path = Path(
        "prompt_templates/implement_prompt_template.md"
    )
    content = template_path.read_text(encoding="utf-8")

    assert "{{SPECIFICATION}}" in content
    assert "{{IMPLEMENTATION_PLAN}}" in content
    assert "{{IMPLEMENTATION_TARGET_PATH}}" in content
    assert "{{TDD_RULES}}" in content
    assert "{{COMPLETION_CONDITIONS}}" in content
    assert "{{STOP_CONDITIONS}}" in content
    assert (
        "{{EXECUTION_RESULT_REPORTING_REQUIREMENTS}}"
        in content
    )

    assert "Implementation Scope" in content
    assert "Allowed Changes" in content
    assert "Forbidden Changes" in content
    assert "TDD Requirements" in content
    assert "Completion Conditions" in content
    assert "Stop Conditions" in content
    assert "Required Execution Result Reporting" in content
    assert "Human Approval Required Conditions" in content

    assert "must not expand" in content.lower()
    assert "human approval" in content.lower()



def test_implement_prompt_template_requires_explicit_test_phase_wrapper():
    template_path = Path(
        "prompt_templates/implement_prompt_template.md"
    )
    content = template_path.read_text(
        encoding="utf-8"
    )

    wrapper = (
        "python -m "
        "infrastructure.specflow_test_wrapper"
    )

    assert (
        f"{wrapper} --phase initial --"
        in content
    )
    assert (
        f"{wrapper} --phase target --"
        in content
    )
    assert (
        f"{wrapper} --phase full --"
        in content
    )
    assert (
        "Do not infer a Test phase"
        in content
    )
    assert (
        "Do not execute a Test command "
        "outside this wrapper"
        in content
    )
