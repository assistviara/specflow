from dataclasses import dataclass


@dataclass(frozen=True)
class AIResponse:
    """AI Runnerから返される実行結果。"""

    content: str
    success: bool
    error_message: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.content, str):
            raise TypeError("content must be a string")

        if not isinstance(self.success, bool):
            raise TypeError("success must be a bool")

        if self.error_message is not None and not isinstance(
            self.error_message, str
        ):
            raise TypeError("error_message must be a string or None")

        if self.success and self.error_message is not None:
            raise ValueError(
                "successful response must not contain an error message"
            )

        if not self.success and not self.error_message:
            raise ValueError(
                "failed response must contain an error message"
            )