from dataclasses import dataclass

class PlanRevisionOutputParseError(ValueError):
    pass

@dataclass(frozen=True)
class PlanRevisionOutput:
    revised_implementation_plan_draft: str
    changes: str
    previous_version_correspondence: str


def parse_plan_revision_output(
    content: str,
) -> PlanRevisionOutput:
    revised_marker = "### REVISED_IMPLEMENTATION_PLAN"
    changes_marker = "### CHANGES"
    correspondence_marker = "### PREVIOUS_VERSION_CORRESPONDENCE"

    required_markers = [
        revised_marker,
        changes_marker,
        correspondence_marker,
    ]

    if any(marker not in content for marker in required_markers):
        raise PlanRevisionOutputParseError(
            "required section is missing"
        )

    revised_index = content.index(revised_marker)
    changes_index = content.index(changes_marker)
    correspondence_index = content.index(correspondence_marker)

    if not (
        revised_index
        < changes_index
        < correspondence_index
    ):
        raise PlanRevisionOutputParseError(
            "sections are out of order"
        )

    revised_start = content.index(revised_marker) + len(revised_marker)
    changes_start = content.index(changes_marker) + len(changes_marker)
    correspondence_start = (
        content.index(correspondence_marker)
        + len(correspondence_marker)
    )

    revised_implementation_plan_draft = content[
        revised_start:content.index(changes_marker)
    ].strip()

    changes = content[
        changes_start:content.index(correspondence_marker)
    ].strip()

    previous_version_correspondence = content[
        correspondence_start:
    ].strip()

    if not all(
        [
            revised_implementation_plan_draft,
            changes,
            previous_version_correspondence,
        ]
    ):
        raise PlanRevisionOutputParseError(
            "required section is empty"
        )

    return PlanRevisionOutput(
        revised_implementation_plan_draft=(
            revised_implementation_plan_draft
        ),
        changes=changes,
        previous_version_correspondence=(
            previous_version_correspondence
        ),
    )