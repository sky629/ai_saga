"""Dice Value Objects.

DiceCheckType represents the type of dice check being performed.
DiceResult represents the outcome of a dice roll with modifiers and success determination.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, computed_field


class DiceCheckType(str, Enum):
    """주사위 체크 유형."""

    COMBAT = "combat"
    SKILL = "skill"
    SOCIAL = "social"
    EXPLORATION = "exploration"


class DiceResult(BaseModel):
    """주사위 굴림 결과를 나타내는 불변 값 객체.

    주사위 굴림, 수정자, DC(난이도)를 포함하여 성공/실패를 판정합니다.
    불변 객체로 상태 변경 시 새 인스턴스를 생성합니다.
    """

    model_config = {"frozen": True}

    roll: int = Field(ge=1, le=20, description="주사위 굴림 결과 (1-20)")
    modifier: int = Field(description="수정자")
    dc: int = Field(ge=1, description="난이도 (DC)")
    check_type: DiceCheckType = Field(description="체크 유형")
    damage: Optional[int] = Field(default=None, description="피해량 (선택)")

    @computed_field
    @property
    def total(self) -> int:
        """굴림 + 수정자의 합계."""
        return self.roll + self.modifier

    @computed_field
    @property
    def is_success(self) -> bool:
        """합계가 DC 이상이면 성공."""
        if self.is_fumble:
            return False
        return self.total >= self.dc

    @computed_field
    @property
    def is_critical(self) -> bool:
        """주사위가 20이면 대성공."""
        return self.roll == 20

    @computed_field
    @property
    def is_fumble(self) -> bool:
        """주사위가 1이면 대실패."""
        return self.roll == 1

    @computed_field
    @property
    def display_text(self) -> str:
        """사용자 친화적인 결과 표시 텍스트."""
        modifier_str = (
            f"+{self.modifier}" if self.modifier >= 0 else str(self.modifier)
        )
        base = f"🎲 1d20{modifier_str} = {self.total} vs DC {self.dc} → "

        if self.is_critical:
            return base + "대성공!"
        elif self.is_fumble:
            return base + "대실패!"
        elif self.is_success:
            return base + "성공!"
        else:
            return base + "실패..."
