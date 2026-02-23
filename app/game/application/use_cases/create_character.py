"""Create Character Use Case."""

from uuid import UUID

from pydantic import BaseModel

from app.common.utils.datetime import get_utc_datetime
from app.common.utils.id_generator import get_uuid7
from app.game.application.ports import (
    CharacterRepositoryInterface,
    GameSessionRepositoryInterface,
    ScenarioRepositoryInterface,
    UserProgressionInterface,
)
from app.game.domain.entities import CharacterEntity, CharacterStats
from app.game.domain.services import UserProgressionService


class CreateCharacterInput(BaseModel):
    """Use Case 입력 DTO."""

    name: str
    description: str
    scenario_id: UUID


class CreateCharacterUseCase:
    """캐릭터 생성 유스케이스."""

    def __init__(
        self,
        character_repository: CharacterRepositoryInterface,
        session_repository: GameSessionRepositoryInterface,
        scenario_repository: ScenarioRepositoryInterface,
        user_progression: UserProgressionInterface,
    ):
        self._character_repo = character_repository
        self._session_repo = session_repository
        self._scenario_repo = scenario_repository
        self._user_progression = user_progression

    async def execute(
        self, user_id: UUID, input_data: CreateCharacterInput
    ) -> CharacterEntity:
        """유스케이스 실행."""
        scenario = await self._scenario_repo.get_by_id(input_data.scenario_id)
        if not scenario or not scenario.is_playable:
            raise ValueError("Scenario not found or inactive")

        user_level = await self._user_progression.get_user_game_level(user_id)
        starting_hp = UserProgressionService.calculate_starting_hp(user_level)

        character = CharacterEntity(
            id=get_uuid7(),
            user_id=user_id,
            scenario_id=scenario.id,
            name=input_data.name,
            description=input_data.description,
            stats=CharacterStats(
                hp=starting_hp, max_hp=starting_hp, level=user_level
            ),
            inventory=[],
            is_active=True,
            created_at=get_utc_datetime(),
        )
        return await self._character_repo.save(character)
