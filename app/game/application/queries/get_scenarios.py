"""Get Scenarios Query.

활성 시나리오 목록을 조회하는 읽기 전용 쿼리.
"""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.game.domain.entities import ScenarioEntity
from app.game.infrastructure.persistence.mappers import ScenarioMapper
from app.game.infrastructure.persistence.models.game_models import Scenario


class ScenarioListItem(BaseModel):
    """시나리오 목록 항목 DTO."""

    model_config = {"frozen": True}

    id: UUID
    name: str
    description: str
    genre: str
    difficulty: str
    max_turns: int
    world_setting: Optional[str] = None
    initial_location: Optional[str] = None
    is_active: bool = True


class GetScenariosQuery:
    """시나리오 목록 조회 쿼리.

    CQRS Query: 읽기 전용, 상태 변경 없음.
    """

    def __init__(self, db: AsyncSession):
        self._db = db

    async def execute(
        self, active_only: bool = True
    ) -> list[ScenarioListItem]:
        """활성 시나리오 목록 조회."""
        query = select(Scenario)

        if active_only:
            query = query.where(Scenario.is_active.is_(True))

        query = query.order_by(Scenario.name)

        result = await self._db.execute(query)
        scenarios = result.scalars().all()

        return [
            ScenarioListItem(
                id=s.id,
                name=s.name,
                description=s.description,
                genre=s.genre,
                difficulty=s.difficulty,
                max_turns=s.max_turns,
                world_setting=s.world_setting,
                initial_location=s.initial_location,
                is_active=s.is_active,
            )
            for s in scenarios
        ]

    async def get_by_id(self, scenario_id: UUID) -> Optional[ScenarioEntity]:
        """ID로 시나리오 조회."""
        result = await self._db.execute(
            select(Scenario).where(Scenario.id == scenario_id)
        )
        orm = result.scalar_one_or_none()

        if orm is None:
            return None

        return ScenarioMapper.to_entity(orm)
