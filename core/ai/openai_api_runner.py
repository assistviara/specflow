from core.ai.ai_request import AIRequest
from core.ai.ai_response import AIResponse
from core.ai.ai_runner import AIRunner


class OpenAIAPIRunner(AIRunner):
    """OpenAI Responses API を利用する AI Runner。"""

    def __init__(
        self,
        client,
        model: str,
    ) -> None:
        self._client = client
        self._model = model

    def run(
        self,
        request: AIRequest,
    ) -> AIResponse:
        try:
            response = self._client.responses.create(
                model=self._model,
                input=request.prompt,
            )

            output_text = response.output_text

            if not isinstance(output_text, str):
                return AIResponse(
                    content="",
                    success=False,
                    error_message="OpenAI API response has no output text",
                )

            return AIResponse(
                content=response.output_text,
                success=True,
            )

        except Exception as ex:
            return AIResponse(
                content="",
                success=False,
                error_message=str(ex),
            )