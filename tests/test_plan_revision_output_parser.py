import pytest

from application.plan_revision_output_parser import (
    PlanRevisionOutput,
    PlanRevisionOutputParseError,
    parse_plan_revision_output,
)


def test_parse_plan_revision_output_returns_sections() -> None:
    content = """### REVISED_IMPLEMENTATION_PLAN

Revised implementation plan content.

### CHANGES

Changed the implementation scope.

### PREVIOUS_VERSION_CORRESPONDENCE

Section 2 corresponds to the revised implementation scope.
"""

    result = parse_plan_revision_output(content)

    assert isinstance(result, PlanRevisionOutput)

    assert result.revised_implementation_plan_draft == (
        "Revised implementation plan content."
    )

    assert result.changes == (
        "Changed the implementation scope."
    )

    assert result.previous_version_correspondence == (
        "Section 2 corresponds to the revised implementation scope."
    )

def test_parse_plan_revision_output_raises_when_section_is_missing() -> None:
    content = """### REVISED_IMPLEMENTATION_PLAN

Revised implementation plan content.

### CHANGES

Changed the implementation scope.
"""

    with pytest.raises(
        PlanRevisionOutputParseError,
        match="required section is missing",
    ):
        parse_plan_revision_output(content)

def test_parse_plan_revision_output_raises_when_sections_are_out_of_order() -> None:
    content = """### CHANGES

Changed the implementation scope.

### REVISED_IMPLEMENTATION_PLAN

Revised implementation plan content.

### PREVIOUS_VERSION_CORRESPONDENCE

Section 2 corresponds to the revised implementation scope.
"""

    with pytest.raises(
        PlanRevisionOutputParseError,
        match="sections are out of order",
    ):
        parse_plan_revision_output(content)

def test_parse_plan_revision_output_raises_when_section_is_empty() -> None:
    content = """### REVISED_IMPLEMENTATION_PLAN


### CHANGES

Changed the implementation scope.

### PREVIOUS_VERSION_CORRESPONDENCE

Section 2 corresponds to the revised implementation scope.
"""

    with pytest.raises(
        PlanRevisionOutputParseError,
        match="required section is empty",
    ):
        parse_plan_revision_output(content)