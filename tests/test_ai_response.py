import pytest

from core.ai.ai_response import AIResponse


def test_successful_ai_response_can_be_created() -> None:
    response = AIResponse(
        content="Generated implementation plan.",
        success=True,
    )

    assert response.content == "Generated implementation plan."
    assert response.success is True
    assert response.error_message is None


def test_failed_ai_response_can_be_created() -> None:
    response = AIResponse(
        content="",
        success=False,
        error_message="AI execution failed",
    )

    assert response.content == ""
    assert response.success is False
    assert response.error_message == "AI execution failed"


def test_successful_response_rejects_error_message() -> None:
    with pytest.raises(
        ValueError,
        match="successful response must not contain an error message",
    ):
        AIResponse(
            content="Generated content",
            success=True,
            error_message="Unexpected error",
        )


def test_failed_response_requires_error_message() -> None:
    with pytest.raises(
        ValueError,
        match="failed response must contain an error message",
    ):
        AIResponse(
            content="",
            success=False,
        )


def test_response_rejects_non_string_content() -> None:
    with pytest.raises(TypeError, match="content must be a string"):
        AIResponse(
            content=123,  # type: ignore[arg-type]
            success=True,
        )


def test_response_rejects_non_bool_success() -> None:
    with pytest.raises(TypeError, match="success must be a bool"):
        AIResponse(
            content="Generated content",
            success="yes",  # type: ignore[arg-type]
        )