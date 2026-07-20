from core.ai.ai_request import AIRequest
from core.ai.dummy_runner import DummyAIRunner


def test_dummy_runner_returns_successful_response() -> None:
    runner = DummyAIRunner()

    request = AIRequest(prompt="Hello")

    response = runner.run(request)

    assert response.success is True
    assert "Hello" in response.content


def test_dummy_runner_returns_dummy_prefix() -> None:
    runner = DummyAIRunner()

    request = AIRequest(prompt="Create a plan")

    response = runner.run(request)

    assert response.content.startswith("[Dummy Response]")