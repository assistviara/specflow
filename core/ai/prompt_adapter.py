from core.ai.ai_request import AIRequest
from core.prompt_builder import PromptResult


class PromptAdapter:
    """PromptResult を AIRequest に変換する。"""

    @staticmethod
    def to_ai_request(prompt_result: PromptResult) -> AIRequest:
        if not prompt_result.is_ready:
            raise ValueError(
                "PromptResult is not ready for AI execution."
            )

        return AIRequest(
            prompt=prompt_result.content,
        )