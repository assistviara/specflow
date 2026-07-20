from abc import ABC, abstractmethod

from core.ai.ai_request import AIRequest
from core.ai.ai_response import AIResponse


class AIRunner(ABC):
    """AI Runner の共通インターフェース。"""

    @abstractmethod
    def run(self, request: AIRequest) -> AIResponse:
        """
        AIを実行し、その結果を返す。

        Args:
            request: AIへの入力

        Returns:
            AIResponse
        """
        raise NotImplementedError