from openai import OpenAI


class OpenAIClientFactory:
    """OpenAIクライアントを生成する。"""

    @staticmethod
    def create() -> OpenAI:
        return OpenAI()