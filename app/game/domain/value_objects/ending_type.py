"""Ending type value object."""

from enum import Enum


class EndingType(str, Enum):
    """게임 엔딩 타입을 나타내는 Enum.

    게임 종료 시 결과 분류에 사용.
    """

    VICTORY = "victory"
    DEFEAT = "defeat"
    NEUTRAL = "neutral"

    @classmethod
    def from_string(cls, value: str) -> "EndingType":
        """문자열에서 EndingType 파싱. 기본값은 NEUTRAL."""
        value_lower = value.lower()
        if "victory" in value_lower or "승리" in value_lower:
            return cls.VICTORY
        elif "defeat" in value_lower or "패배" in value_lower:
            return cls.DEFEAT
        return cls.NEUTRAL
