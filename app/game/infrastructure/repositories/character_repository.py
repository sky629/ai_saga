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
        import logging

        logger = logging.getLogger(__name__)

        result = await self._db.execute(
            select(Character).where(Character.id == character.id)
        )
        orm = result.scalar_one_or_none()

        if orm is None:
            logger.info(f"[DEBUG] Creating new character: {character.id}")
            orm = Character(
                id=character.id,
                user_id=character.user_id,
                name=character.name,
                description=character.description,
                scenario_id=character.scenario_id,
                stats=character.stats.model_dump(),
                inventory=character.inventory,
                is_active=character.is_active,
                created_at=character.created_at,
            )
            self._db.add(orm)
        else:
            logger.info(f"[DEBUG] Updating existing character: {character.id}")
            logger.info(
                f"[DEBUG] ORM before update: inventory={orm.inventory}, stats={orm.stats}"
            )
            updates = CharacterMapper.to_dict(character)
            logger.info(f"[DEBUG] Updates to apply: {updates}")
            for key, value in updates.items():
                setattr(orm, key, value)
            logger.info(
                f"[DEBUG] ORM after update: inventory={orm.inventory}, stats={orm.stats}"
            )

        await self._db.flush()
        await self._db.refresh(orm)

        return CharacterMapper.to_entity(orm)

    async def delete(self, character_id: UUID) -> None:
        """캐릭터 삭제."""
        from sqlalchemy import delete as sql_delete

        await self._db.execute(
            sql_delete(Character).where(Character.id == character_id)
        )
        await self._db.flush()
