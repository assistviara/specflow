from unittest.mock import Mock, patch

from core.ai.openai_client_factory import OpenAIClientFactory


def test_create_returns_openai_client():
    expected_client = Mock()

    with patch(
        "core.ai.openai_client_factory.OpenAI",
        return_value=expected_client,
    ) as mock_openai:
        actual_client = OpenAIClientFactory.create()

    mock_openai.assert_called_once_with()
    assert actual_client is expected_client