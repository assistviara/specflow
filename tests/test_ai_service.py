from unittest.mock import Mock

from core.ai.ai_request import AIRequest
from core.ai.ai_response import AIResponse
from core.ai.ai_service import AIService


def test_run_passes_request_to_runner_and_returns_response():
    request = Mock(spec=AIRequest)
    expected_response = Mock(spec=AIResponse)

    runner = Mock()
    runner.run.return_value = expected_response

    service = AIService(runner=runner)

    actual_response = service.run(request)

    runner.run.assert_called_once_with(request)
    assert actual_response is expected_response