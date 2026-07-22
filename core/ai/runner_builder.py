from core.ai.openai_api_runner import OpenAIAPIRunner
from core.ai.openai_client_factory import OpenAIClientFactory


def create_openai_runner(model: str) -> OpenAIAPIRunner:
    client = OpenAIClientFactory.create()

    return OpenAIAPIRunner(
        client=client,
        model=model,
    )