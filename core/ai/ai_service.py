from core.ai.ai_request import AIRequest
from core.ai.ai_response import AIResponse
from core.ai.ai_runner import AIRunner


class AIService:
    """AI実行処理をAIRunnerへ委譲する。"""

    def __init__(self, runner: AIRunner) -> None:
        self._runner = runner

    def run(self, request: AIRequest) -> AIResponse:
        return self._runner.run(request)