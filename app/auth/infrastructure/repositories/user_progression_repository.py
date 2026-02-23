"""유저 게임 진행도 저장소 구현체."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.infrastructure.persistence.mappers import UserMapper
from app.auth.infrastructure.persistence.models.user_models import (
    User as UserModel,
)
from app.common.exception import NotFound
from app.game.application.ports import (
    UserProgressionInterface,
    UserProgressionResult,
)


class UserProgressionRepositoryImpl(UserProgressionInterface):
    """유저 게임 진행도 저장소 구현체.

    Auth 인프라에 위치하지만 Game의 Port를 구현합니다 (의존성 역전).
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_user_game_level(self, user_id: UUID) -> int:
        """유저의 현재 게임 레벨 조회."""
        result = await self._db.execute(
            select(UserModel.game_level).where(UserModel.id == user_id)
        )
        game_level = result.scalar_one_or_none()
        if game_level is None:
            raise NotFound(f"유저를 찾을 수 없습니다: {user_id}")
        return game_level

    async def award_game_experience(
        self, user_id: UUID, xp: int
    ) -> UserProgressionResult:
        """유저에게 게임 경험치 부여 후 결과 반환."""
        result = await self._db.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        user_orm = result.scalar_one_or_none()
        if user_orm is None:
            raise NotFound(f"유저를 찾을 수 없습니다: {user_id}")

        user_entity = UserMapper.to_entity(user_orm)
        old_level = user_entity.game_level

        updated_entity = user_entity.gain_game_experience(xp)

        # ORM 업데이트
        user_orm.game_level = updated_entity.game_level
        user_orm.game_experience = updated_entity.game_experience
        user_orm.game_current_experience = (
            updated_entity.game_current_experience
        )
        await self._db.flush()

        levels_gained = updated_entity.game_level - old_level

        return UserProgressionResult(
            game_level=updated_entity.game_level,
            game_experience=updated_entity.game_experience,
            game_current_experience=(updated_entity.game_current_experience),
            leveled_up=levels_gained > 0,
            levels_gained=levels_gained,
        )
