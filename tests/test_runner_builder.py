from unittest.mock import Mock, patch

from core.ai.runner_builder import create_openai_runner


def test_create_openai_runner():
    mock_client = Mock()
    mock_runner = Mock()

    with (
        patch(
            "core.ai.runner_builder.OpenAIClientFactory.create",
            return_value=mock_client,
        ) as mock_create,
        patch(
            "core.ai.runner_builder.OpenAIAPIRunner",
            return_value=mock_runner,
        ) as mock_runner_class,
    ):
        runner = create_openai_runner("gpt-5.5")

    mock_create.assert_called_once_with()

    mock_runner_class.assert_called_once_with(
        client=mock_client,
        model="gpt-5.5",
    )

    assert runner is mock_runner