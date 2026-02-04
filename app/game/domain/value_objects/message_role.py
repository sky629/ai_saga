"""Message role value object."""

from enum import Enum


class MessageRole(str, Enum):
    """게임 메시지 역할을 나타내는 Enum.

    대화 히스토리에서 발신자 구분에 사용.
    """

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

    def is_player(self) -> bool:
        """플레이어 메시지인지 확인."""
        return self == MessageRole.USER

    def is_ai(self) -> bool:
        """AI 응답인지 확인."""
        return self == MessageRole.ASSISTANT
