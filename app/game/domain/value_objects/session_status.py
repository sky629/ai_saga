"""Session status value object."""

from enum import Enum


class SessionStatus(str, Enum):
    """게임 세션 상태를 나타내는 Enum.
    
    str을 상속하여 JSON 직렬화 및 ORM 호환성 보장.
    """
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ENDED = "ended"
    
    @classmethod
    def is_playable(cls, status: "SessionStatus") -> bool:
        """플레이 가능한 상태인지 확인."""
        return status == cls.ACTIVE
