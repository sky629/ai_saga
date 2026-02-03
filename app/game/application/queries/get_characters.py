"""Get Characters Query."""

from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.game.domain.entities import CharacterEntity
from app.game.infrastructure.persistence.mappers import CharacterMapper
from app.game.infrastructure.persistence.models.game_models import Character

class GetCharactersQuery:
    """사용자의 캐릭터 목록을 조회하는 쿼리."""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def execute(self, user_id: UUID) -> list[CharacterEntity]:
        """사용자의 모든 활성 캐릭터 조회."""
        result = await self._db.execute(
            select(Character).where(
                Character.user_id == user_id,
                Character.is_active.is_(True)
            )
        )
        orms = result.scalars().all()
        return [CharacterMapper.to_entity(orm) for orm in orms]
