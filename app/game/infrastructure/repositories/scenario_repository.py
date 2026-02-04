"""Scenario Repository Implementation."""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.game.application.ports import ScenarioRepositoryInterface
from app.game.domain.entities import ScenarioEntity
from app.game.infrastructure.persistence.mappers import ScenarioMapper
from app.game.infrastructure.persistence.models.game_models import Scenario


class ScenarioRepositoryImpl(ScenarioRepositoryInterface):
    """Scenario 저장소 구현체."""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_by_id(self, scenario_id: UUID) -> Optional[ScenarioEntity]:
        """ID로 시나리오 조회."""
        result = await self._db.execute(
            select(Scenario).where(Scenario.id == scenario_id)
        )
        orm = result.scalar_one_or_none()

        if orm is None:
            return None

        return ScenarioMapper.to_entity(orm)

    async def get_all_active(self) -> list[ScenarioEntity]:
        """모든 활성 시나리오 조회."""
        result = await self._db.execute(
            select(Scenario).where(Scenario.is_active.is_(True))
        )
        orms = result.scalars().all()

        return [ScenarioMapper.to_entity(orm) for orm in orms]
