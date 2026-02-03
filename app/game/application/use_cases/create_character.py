"""Create Character Use Case."""

from uuid import UUID, uuid4
from pydantic import BaseModel
from app.game.application.ports import CharacterRepositoryInterface
from app.game.domain.entities import CharacterEntity
from app.game.domain.entities.character import CharacterStats

class CreateCharacterInput(BaseModel):
    """캐릭터 생성 입력 DTO."""
    name: str
    description: str | None = None

class CreateCharacterUseCase:
    """새 캐릭터를 생성하는 유스케이스."""

    def __init__(self, character_repository: CharacterRepositoryInterface):
        self.character_repository = character_repository

    async def execute(self, user_id: UUID, input_data: CreateCharacterInput) -> CharacterEntity:
        """새 캐릭터 생성 및 저장."""
        character = CharacterEntity(
            id=uuid4(),
            user_id=user_id,
            name=input_data.name,
            description=input_data.description,
            stats=CharacterStats(hp=100, max_hp=100, level=1),
            inventory=[],
            is_active=True
        )
        return await self.character_repository.save(character)
