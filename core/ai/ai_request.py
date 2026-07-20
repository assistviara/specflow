from dataclasses import dataclass


@dataclass(frozen=True)
class AIRequest:
    """AI Runnerに渡す入力データ。"""

    prompt: str

    def __post_init__(self) -> None:
        if not isinstance(self.prompt, str):
            raise TypeError("prompt must be a string")

        if not self.prompt.strip():
            raise ValueError("prompt must not be empty")