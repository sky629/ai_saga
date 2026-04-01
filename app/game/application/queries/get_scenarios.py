"""Get Scenarios Query.

활성 시나리오 목록을 조회하는 읽기 전용 쿼리.
"""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.game.application.ports import ScenarioRepositoryInterface
from app.game.domain.entities import ScenarioEntity


class ScenarioListItem(BaseModel):
    """시나리오 목록 항목 DTO."""

    model_config = {"frozen": True}

    id: UUID
    name: str
    description: str
    game_type: str
    genre: str
    difficulty: str
    max_turns: int
    tags: list[str]
    thumbnail_url: Optional[str] = None
    hook: Optional[str] = None
    recommended_for: Optional[str] = None
    world_setting: Optional[str] = None
    initial_location: Optional[str] = None
    is_active: bool = True


class GetScenariosQuery:
    """시나리오 목록 조회 쿼리.

    CQRS Query: 읽기 전용, 상태 변경 없음.
    """

    def __init__(self, scenario_repo: ScenarioRepositoryInterface):
        self._scenario_repo = scenario_repo

    async def execute(
        self, active_only: bool = True
    ) -> list[ScenarioListItem]:
        """활성 시나리오 목록 조회."""
        scenarios = await self._scenario_repo.get_all(active_only=active_only)

        return [
            ScenarioListItem(
                id=s.id,
                name=s.name,
                description=s.description,
                game_type=s.game_type.value,
                genre=s.genre.value,
                difficulty=s.difficulty.value,
                max_turns=s.max_turns,
                tags=s.tags,
                thumbnail_url=s.thumbnail_url,
                hook=s.hook,
                recommended_for=s.recommended_for,
                world_setting=s.world_setting,
                initial_location=s.initial_location,
                is_active=s.is_active,
            )
            for s in scenarios
        ]

    async def get_by_id(self, scenario_id: UUID) -> Optional[ScenarioEntity]:
        """ID로 시나리오 조회."""
        return await self._scenario_repo.get_by_id(scenario_id)
