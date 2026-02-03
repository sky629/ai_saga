"""Character Repository Implementation."""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.game.application.ports import CharacterRepositoryInterface
from app.game.domain.entities import CharacterEntity
from app.game.infrastructure.persistence.mappers import CharacterMapper
from app.game.infrastructure.persistence.models.game_models import Character


class CharacterRepositoryImpl(CharacterRepositoryInterface):
    """Character 저장소 구현체."""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_by_id(self, character_id: UUID) -> Optional[CharacterEntity]:
        """ID로 캐릭터 조회."""
        result = await self._db.execute(
            select(Character).where(Character.id == character_id)
        )
        orm = result.scalar_one_or_none()
        
        if orm is None:
            return None
        
        return CharacterMapper.to_entity(orm)

    async def get_by_user(self, user_id: UUID) -> list[CharacterEntity]:
        """사용자의 모든 캐릭터 조회."""
        result = await self._db.execute(
            select(Character).where(
                Character.user_id == user_id,
                Character.is_active.is_(True),
            )
        )
        orms = result.scalars().all()
        
        return [CharacterMapper.to_entity(orm) for orm in orms]

    async def save(self, character: CharacterEntity) -> CharacterEntity:
        """캐릭터 저장."""
        result = await self._db.execute(
            select(Character).where(Character.id == character.id)
        )
        orm = result.scalar_one_or_none()

        if orm is None:
            orm = Character(
                id=character.id,
                user_id=character.user_id,
                name=character.name,
                description=character.description,
                stats=character.stats.model_dump(),
                inventory=character.inventory,
                is_active=character.is_active,
                created_at=character.created_at,
            )
            self._db.add(orm)
        else:
            updates = CharacterMapper.to_dict(character)
            for key, value in updates.items():
                setattr(orm, key, value)

        await self._db.commit()
        await self._db.refresh(orm)
        
        return CharacterMapper.to_entity(orm)
