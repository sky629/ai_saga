"""게임 액션 타입 값 객체."""

from enum import Enum


class ActionType(str, Enum):
    """플레이어 액션 타입."""

    COMBAT = "combat"
    SOCIAL = "social"
    SKILL = "skill"
    MOVEMENT = "movement"
    OBSERVATION = "observation"
    REST = "rest"
    EXPLORATION = "exploration"

    @property
    def requires_dice(self) -> bool:
        """해당 액션 타입이 주사위 판정을 요구하는지 반환."""
        return self in {
            ActionType.COMBAT,
            ActionType.SOCIAL,
            ActionType.SKILL,
            ActionType.EXPLORATION,
        }
