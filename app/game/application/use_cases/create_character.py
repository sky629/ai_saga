"""Create Character Use Case."""

from uuid import UUID

from pydantic import BaseModel

from app.common.utils.datetime import get_utc_datetime
from app.common.utils.id_generator import get_uuid7
from app.game.application.ports import (
    CharacterRepositoryInterface,
    GameSessionRepositoryInterface,
)
from app.game.domain.entities import CharacterEntity, CharacterStats


class CreateCharacterInput(BaseModel):
    """Use Case 입력 DTO."""

    name: str
    description: str


class CreateCharacterUseCase:
    """캐릭터 생성 유스케이스."""

    def __init__(
        self,
        character_repository: CharacterRepositoryInterface,
        session_repository: GameSessionRepositoryInterface,
    ):
        self._character_repo = character_repository
        self._session_repo = session_repository

    async def execute(
        self, user_id: UUID, input_data: CreateCharacterInput
    ) -> CharacterEntity:
        """유스케이스 실행."""
        # 1. Create character entity
        character = CharacterEntity(
            id=get_uuid7(),
            user_id=user_id,
            name=input_data.name,
            description=input_data.description,
            stats=CharacterStats(hp=100, max_hp=100, level=1),
            inventory=[],
            is_active=True,
            created_at=get_utc_datetime(),
        )
        return await self._character_repo.save(character)
