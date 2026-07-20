import pytest

from core.ai.ai_request import AIRequest
from core.ai.prompt_adapter import PromptAdapter
from core.prompt_builder import PromptResult


def test_prompt_adapter_creates_ai_request() -> None:
    result = PromptResult(
        content="Hello AI",
        undefined_variables=[],
        unused_context=[],
        warnings=[],
    )

    request = PromptAdapter.to_ai_request(result)

    assert isinstance(request, AIRequest)
    assert request.prompt == "Hello AI"


def test_prompt_adapter_rejects_unready_prompt() -> None:
    result = PromptResult(
        content="Hello AI",
        undefined_variables=["PROJECT_NAME"],
        unused_context=[],
        warnings=[],
    )

    with pytest.raises(
        ValueError,
        match="PromptResult is not ready for AI execution.",
    ):
        PromptAdapter.to_ai_request(result)