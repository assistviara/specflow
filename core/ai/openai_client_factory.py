from openai import OpenAI


class OpenAIClientFactory:
    @staticmethod
    def create():
        return OpenAI()