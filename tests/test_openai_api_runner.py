from unittest.mock import Mock

from core.ai.ai_request import AIRequest
from core.ai.openai_api_runner import OpenAIAPIRunner


def test_openai_api_runner_returns_success_response() -> None:
    client = Mock()

    api_response = Mock()
    api_response.output_text = "Implementation Planを生成しました。"

    client.responses.create.return_value = api_response

    runner = OpenAIAPIRunner(
        client=client,
        model="gpt-5.5",
    )

    request = AIRequest(
        prompt="Implementation Planを生成してください。"
    )

    response = runner.run(request)

    client.responses.create.assert_called_once_with(
        model="gpt-5.5",
        input=request.prompt,
    )

    assert response.content == (
        "Implementation Planを生成しました。"
    )
    assert response.success is True
    assert response.error_message is None

def test_openai_api_runner_returns_failure_response_when_api_raises() -> None:
    client = Mock()

    client.responses.create.side_effect = RuntimeError(
        "OpenAI API error"
    )

    runner = OpenAIAPIRunner(
        client=client,
        model="gpt-5.5",
    )

    request = AIRequest(
        prompt="Implementation Planを生成してください。"
    )

    response = runner.run(request)

    client.responses.create.assert_called_once_with(
        model="gpt-5.5",
        input=request.prompt,
    )

    assert response.content == ""
    assert response.success is False
    assert response.error_message == "OpenAI API error"

def test_openai_api_runner_returns_failure_when_output_text_is_invalid() -> None:
    client = Mock()

    api_response = Mock()
    api_response.output_text = None

    client.responses.create.return_value = api_response

    runner = OpenAIAPIRunner(
        client=client,
        model="gpt-5.5",
    )

    request = AIRequest(
        prompt="Implementation Planを生成してください。"
    )

    response = runner.run(request)

    assert response.content == ""
    assert response.success is False
    assert response.error_message == "OpenAI API response has no output text"