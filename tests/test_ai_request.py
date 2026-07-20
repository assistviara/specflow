import pytest

from core.ai.ai_request import AIRequest


def test_ai_request_can_be_created() -> None:
    request = AIRequest(prompt="Create an implementation plan.")

    assert request.prompt == "Create an implementation plan."


def test_ai_request_rejects_empty_prompt() -> None:
    with pytest.raises(ValueError, match="prompt must not be empty"):
        AIRequest(prompt="")


def test_ai_request_rejects_whitespace_only_prompt() -> None:
    with pytest.raises(ValueError, match="prompt must not be empty"):
        AIRequest(prompt="   ")


def test_ai_request_rejects_non_string_prompt() -> None:
    with pytest.raises(TypeError, match="prompt must be a string"):
        AIRequest(prompt=123)  # type: ignore[arg-type]