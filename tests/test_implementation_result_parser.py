from application.implementation_result_parser import (
    ImplementationResultParser,
)


def test_parse_valid_implementation_result() -> None:
    raw_text = """## Implementation Summary
TEST_REQUIRED: YES
Approved scope implementation completed.

## Changed Files
application/example.py

## Executed Commands
python -m pytest -q tests/test_example.py

## Test Execution Status
COMPLETED

## Test Result
PASS

## Test Execution Error
TECHNICAL_RETRY_SAFE: NO
TECHNICAL_RETRY_OPERATION: NONE

## Errors
NONE

## Warnings
NONE

## Incomplete Items
NONE

## Human Approval Required
NONE
"""

    result = ImplementationResultParser.parse(raw_text)

    assert result.implementation_summary == (
        "TEST_REQUIRED: YES\n"
        "Approved scope implementation completed."
    )
    assert result.changed_files == "application/example.py"
    assert result.executed_commands == "python -m pytest -q tests/test_example.py"
    assert result.test_execution_status == "COMPLETED"
    assert result.test_result == "PASS"
    assert result.test_required is True
    assert result.technical_retry_safe is False
    assert result.technical_retry_operation is None
    assert result.errors == "NONE"
    assert result.warnings == "NONE"
    assert result.incomplete_items == "NONE"
    assert result.human_approval_required == "NONE"


import pytest

from application.implementation_result_parser import (
    ImplementationResultParseError,
)


def _valid_raw_text() -> str:
    return """## Implementation Summary
TEST_REQUIRED: YES
Approved scope implementation completed.

## Changed Files
application/example.py

## Executed Commands
python -m pytest -q tests/test_example.py

## Test Execution Status
COMPLETED

## Test Result
PASS

## Test Execution Error
TECHNICAL_RETRY_SAFE: NO
TECHNICAL_RETRY_OPERATION: NONE

## Errors
NONE

## Warnings
NONE

## Incomplete Items
NONE

## Human Approval Required
NONE
"""


def test_parse_rejects_missing_required_section() -> None:
    raw_text = _valid_raw_text().replace(
        "## Warnings\nNONE\n\n",
        "",
    )

    with pytest.raises(
        ImplementationResultParseError,
        match="required section is missing",
    ):
        ImplementationResultParser.parse(raw_text)


def test_parse_rejects_sections_out_of_order() -> None:
    raw_text = _valid_raw_text().replace(
        "## Test Execution Status\nCOMPLETED\n\n"
        "## Test Result\nPASS",
        "## Test Result\nPASS\n\n"
        "## Test Execution Status\nCOMPLETED",
    )

    with pytest.raises(
        ImplementationResultParseError,
        match="sections are out of order",
    ):
        ImplementationResultParser.parse(raw_text)


def test_parse_rejects_invalid_test_execution_status() -> None:
    raw_text = _valid_raw_text().replace(
        "## Test Execution Status\nCOMPLETED",
        "## Test Execution Status\nBROKEN",
    )

    with pytest.raises(
        ImplementationResultParseError,
        match="invalid Test Execution Status",
    ):
        ImplementationResultParser.parse(raw_text)


def test_parse_rejects_invalid_test_result() -> None:
    raw_text = _valid_raw_text().replace(
        "## Test Result\nPASS",
        "## Test Result\nSUCCESS",
    )

    with pytest.raises(
        ImplementationResultParseError,
        match="invalid Test Result",
    ):
        ImplementationResultParser.parse(raw_text)


def test_parse_rejects_missing_test_required_metadata() -> None:
    raw_text = _valid_raw_text().replace(
        "TEST_REQUIRED: YES\n",
        "",
    )

    with pytest.raises(
        ImplementationResultParseError,
        match="invalid TEST_REQUIRED metadata",
    ):
        ImplementationResultParser.parse(raw_text)


def test_parse_rejects_invalid_test_required_metadata() -> None:
    raw_text = _valid_raw_text().replace(
        "TEST_REQUIRED: YES",
        "TEST_REQUIRED: MAYBE",
    )

    with pytest.raises(
        ImplementationResultParseError,
        match="invalid TEST_REQUIRED metadata",
    ):
        ImplementationResultParser.parse(raw_text)


def test_parse_test_required_no_as_false() -> None:
    raw_text = _valid_raw_text().replace(
        "TEST_REQUIRED: YES",
        "TEST_REQUIRED: NO",
    ).replace(
        "## Test Execution Status\nCOMPLETED",
        "## Test Execution Status\nNOT_RUN",
    ).replace(
        "## Test Result\nPASS",
        "## Test Result\nNONE",
    )

    result = ImplementationResultParser.parse(raw_text)

    assert result.test_required is False


def test_parse_technical_retry_safe_yes_as_true() -> None:
    raw_text = _valid_raw_text().replace(
        "TECHNICAL_RETRY_SAFE: NO",
        "TECHNICAL_RETRY_SAFE: YES",
    ).replace(
        "TECHNICAL_RETRY_OPERATION: NONE",
        "TECHNICAL_RETRY_OPERATION: python -m pytest -q tests/test_example.py",
    )

    result = ImplementationResultParser.parse(raw_text)

    assert result.technical_retry_safe is True
    assert (
        result.technical_retry_operation
        == "python -m pytest -q tests/test_example.py"
    )


def test_parse_technical_retry_safe_unknown_as_none() -> None:
    raw_text = _valid_raw_text().replace(
        "TECHNICAL_RETRY_SAFE: NO",
        "TECHNICAL_RETRY_SAFE: UNKNOWN",
    )

    result = ImplementationResultParser.parse(raw_text)

    assert result.technical_retry_safe is None
    assert result.technical_retry_operation is None


def test_parse_rejects_missing_technical_retry_safe_metadata() -> None:
    raw_text = _valid_raw_text().replace(
        "TECHNICAL_RETRY_SAFE: NO\n",
        "",
    )

    with pytest.raises(
        ImplementationResultParseError,
        match="invalid TECHNICAL_RETRY_SAFE metadata",
    ):
        ImplementationResultParser.parse(raw_text)


def test_parse_rejects_invalid_technical_retry_safe_metadata() -> None:
    raw_text = _valid_raw_text().replace(
        "TECHNICAL_RETRY_SAFE: NO",
        "TECHNICAL_RETRY_SAFE: MAYBE",
    )

    with pytest.raises(
        ImplementationResultParseError,
        match="invalid TECHNICAL_RETRY_SAFE metadata",
    ):
        ImplementationResultParser.parse(raw_text)


def test_parse_rejects_missing_technical_retry_operation_metadata() -> None:
    raw_text = _valid_raw_text().replace(
        "TECHNICAL_RETRY_OPERATION: NONE\n",
        "",
    )

    with pytest.raises(
        ImplementationResultParseError,
        match="invalid TECHNICAL_RETRY_OPERATION metadata",
    ):
        ImplementationResultParser.parse(raw_text)


def test_parse_rejects_yes_with_none_operation() -> None:
    raw_text = _valid_raw_text().replace(
        "TECHNICAL_RETRY_SAFE: NO",
        "TECHNICAL_RETRY_SAFE: YES",
    )

    with pytest.raises(
        ImplementationResultParseError,
        match="invalid TECHNICAL_RETRY_OPERATION metadata",
    ):
        ImplementationResultParser.parse(raw_text)


def test_parse_rejects_no_with_concrete_operation() -> None:
    raw_text = _valid_raw_text().replace(
        "TECHNICAL_RETRY_OPERATION: NONE",
        "TECHNICAL_RETRY_OPERATION: python -m pytest -q",
    )

    with pytest.raises(
        ImplementationResultParseError,
        match="invalid TECHNICAL_RETRY_OPERATION metadata",
    ):
        ImplementationResultParser.parse(raw_text)


def test_parse_rejects_unknown_with_concrete_operation() -> None:
    raw_text = _valid_raw_text().replace(
        "TECHNICAL_RETRY_SAFE: NO",
        "TECHNICAL_RETRY_SAFE: UNKNOWN",
    ).replace(
        "TECHNICAL_RETRY_OPERATION: NONE",
        "TECHNICAL_RETRY_OPERATION: python -m pytest -q",
    )

    with pytest.raises(
        ImplementationResultParseError,
        match="invalid TECHNICAL_RETRY_OPERATION metadata",
    ):
        ImplementationResultParser.parse(raw_text)


def test_parse_rejects_empty_required_section() -> None:
    raw_text = _valid_raw_text().replace(
        "## Warnings\nNONE\n\n",
        "## Warnings\n\n",
    )

    with pytest.raises(
        ImplementationResultParseError,
        match="required section is empty",
    ):
        ImplementationResultParser.parse(raw_text)
