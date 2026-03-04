"""Get Characters Query."""

from uuid import UUID

from app.game.application.ports import CharacterRepositoryInterface
from app.game.domain.entities import CharacterEntity


class GetCharactersQuery:
    """사용자의 캐릭터 목록을 조회하는 쿼리."""

    def __init__(self, character_repo: CharacterRepositoryInterface):
        self._character_repo = character_repo

    async def execute(self, user_id: UUID) -> list[CharacterEntity]:
        """사용자의 모든 활성 캐릭터 조회."""
        return await self._character_repo.get_by_user(user_id)
