# core/ai/ai_service.py

class AIService:
    def __init__(self, runner):
        self._runner = runner

    def run(self, request):
        return self._runner.run(request)