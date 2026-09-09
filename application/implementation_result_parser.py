from dataclasses import dataclass


@dataclass(frozen=True)
class ImplementationResult:
    implementation_summary: str
    changed_files: str
    executed_commands: str
    test_execution_status: str
    test_result: str
    test_execution_error: str
    errors: str
    warnings: str
    incomplete_items: str
    human_approval_required: str
    test_required: bool
    technical_retry_safe: bool | None
    technical_retry_operation: str | None


class ImplementationResultParseError(ValueError):
    pass


_REQUIRED_HEADINGS = [
    "## Implementation Summary",
    "## Changed Files",
    "## Executed Commands",
    "## Test Execution Status",
    "## Test Result",
    "## Test Execution Error",
    "## Errors",
    "## Warnings",
    "## Incomplete Items",
    "## Human Approval Required",
]


class ImplementationResultParser:
    @staticmethod
    def parse(content: str) -> ImplementationResult:
        try:
            positions = [
                content.index(heading)
                for heading in _REQUIRED_HEADINGS
            ]
        except ValueError as exc:
            raise ImplementationResultParseError(
                "required section is missing"
            ) from exc

        if positions != sorted(positions):
            raise ImplementationResultParseError(
                "sections are out of order"
            )

        sections: list[str] = []

        for index, heading in enumerate(_REQUIRED_HEADINGS):
            start = positions[index] + len(heading)

            if index + 1 < len(_REQUIRED_HEADINGS):
                end = positions[index + 1]
            else:
                end = len(content)

            sections.append(content[start:end].strip())

        if any(not section for section in sections):
            raise ImplementationResultParseError(
                "required section is empty"
            )

        implementation_summary = sections[0]
        test_execution_error = sections[5]

        test_execution_status = sections[3]
        if test_execution_status not in {
            "COMPLETED",
            "ERROR",
            "NOT_RUN",
        }:
            raise ImplementationResultParseError(
                "invalid Test Execution Status"
            )

        test_result = sections[4]
        if test_result not in {
            "PASS",
            "FAIL",
            "NONE",
        }:
            raise ImplementationResultParseError(
                "invalid Test Result"
            )

        if "TEST_REQUIRED: YES" in implementation_summary:
            test_required = True
        elif "TEST_REQUIRED: NO" in implementation_summary:
            test_required = False
        else:
            raise ImplementationResultParseError(
                "invalid TEST_REQUIRED metadata"
            )

        if "TECHNICAL_RETRY_SAFE: YES" in test_execution_error:
            technical_retry_safe = True
        elif "TECHNICAL_RETRY_SAFE: NO" in test_execution_error:
            technical_retry_safe = False
        elif "TECHNICAL_RETRY_SAFE: UNKNOWN" in test_execution_error:
            technical_retry_safe = None
        else:
            raise ImplementationResultParseError(
                "invalid TECHNICAL_RETRY_SAFE metadata"
            )

        operation_prefix = "TECHNICAL_RETRY_OPERATION:"
        operation_value = None

        for line in test_execution_error.splitlines():
            if line.startswith(operation_prefix):
                operation_value = line[len(operation_prefix):].strip()
                break

        if not operation_value:
            raise ImplementationResultParseError(
                "invalid TECHNICAL_RETRY_OPERATION metadata"
            )

        if technical_retry_safe is True:
            if operation_value == "NONE":
                raise ImplementationResultParseError(
                    "invalid TECHNICAL_RETRY_OPERATION metadata"
                )
            technical_retry_operation = operation_value
        else:
            if operation_value != "NONE":
                raise ImplementationResultParseError(
                    "invalid TECHNICAL_RETRY_OPERATION metadata"
                )
            technical_retry_operation = None

        return ImplementationResult(
            implementation_summary=implementation_summary,
            changed_files=sections[1],
            executed_commands=sections[2],
            test_execution_status=test_execution_status,
            test_result=test_result,
            test_execution_error=test_execution_error,
            errors=sections[6],
            warnings=sections[7],
            incomplete_items=sections[8],
            human_approval_required=sections[9],
            test_required=test_required,
            technical_retry_safe=technical_retry_safe,
            technical_retry_operation=technical_retry_operation,
        )
