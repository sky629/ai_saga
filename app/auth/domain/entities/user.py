"""User Entity."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.auth.domain.value_objects import UserLevel


class UserEntity(BaseModel):
    """사용자 도메인 엔티티."""

    model_config = {"frozen": True}

    id: UUID
    email: str
    name: str
    profile_image_url: Optional[str] = None
    user_level: UserLevel = UserLevel.NORMAL
    is_active: bool = True
    email_verified: bool = False
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None

    game_level: int = Field(ge=1, default=1)
    game_experience: int = Field(ge=0, default=0)
    game_current_experience: int = Field(ge=0, default=0)

    def game_experience_for_next_level(self) -> int:
        """다음 레벨까지 필요한 게임 경험치."""
        return self.game_level * 300

    def gain_game_experience(self, amount: int) -> "UserEntity":
        """게임 경험치 획득 및 자동 레벨업.

        Args:
            amount: 획득할 경험치량

        Returns:
            업데이트된 새 UserEntity (레벨업 포함)
        """
        new_exp = self.game_experience + amount
        new_current_exp = self.game_current_experience + amount
        updated = self.model_copy(
            update={
                "game_experience": new_exp,
                "game_current_experience": new_current_exp,
            }
        )

        while (
            updated.game_current_experience
            >= updated.game_experience_for_next_level()
        ):
            updated = updated._game_level_up_once()

        return updated

    def _game_level_up_once(self) -> "UserEntity":
        """한 게임 레벨 상승 (내부 메서드)."""
        required_exp = self.game_experience_for_next_level()
        remaining_exp = self.game_current_experience - required_exp

        return self.model_copy(
            update={
                "game_level": self.game_level + 1,
                "game_current_experience": remaining_exp,
            }
        )
