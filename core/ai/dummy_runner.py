from core.ai.ai_request import AIRequest
from core.ai.ai_response import AIResponse
from core.ai.ai_runner import AIRunner


class DummyAIRunner(AIRunner):
    """テスト用のAI Runner。"""

    def run(self, request: AIRequest) -> AIResponse:
        return AIResponse(
            content=f"[Dummy Response]\n\n{request.prompt}",
            success=True,
        )