import pytest

from core.ai.ai_runner import AIRunner


def test_ai_runner_cannot_be_instantiated() -> None:
    with pytest.raises(TypeError):
        AIRunner()