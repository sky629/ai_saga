"""Delete Session Use Case."""

from uuid import UUID

from app.game.application.ports import (
    CharacterRepositoryInterface,
    GameSessionRepositoryInterface,
)


class DeleteSessionUseCase:
    """게임 세션 삭제 유스케이스."""

    def __init__(
        self,
        session_repository: GameSessionRepositoryInterface,
        character_repository: CharacterRepositoryInterface,
    ):
        self._session_repo = session_repository
        self._character_repo = character_repository

    async def execute(self, user_id: UUID, session_id: UUID) -> None:
        """세션 삭제 실행.

        Args:
            user_id: 요청한 사용자 ID
            session_id: 삭제할 세션 ID

        Raises:
            ValueError: 세션이 없거나 사용자 소유가 아닌 경우
        """
        # 1. 세션 조회
        session = await self._session_repo.get_by_id(session_id)
        if not session:
            # 보안상 404와 동일하게 처리하거나, 명시적으로 없음을 알림
            # 여기서는 멱등성을 위해 없는 경우 조용히 성공할 수도 있지만,
            # 일반적으로 리소스가 없으면 404를 반환하는 것이 RESTful함.
            # 하지만 UseCase에서는 비즈니스 로직 상 "내 세션이 아님"으로 취급하여 에러 발생.
            raise ValueError("Session not found")

        # 2. 소유권 확인 (Session -> Character -> User)
        character = await self._character_repo.get_by_id(session.character_id)
        if not character or character.user_id != user_id:
            raise ValueError("Session not found or authentication failed")

        # 3. 세션 삭제
        await self._session_repo.delete(session_id)

        # 4. 캐릭터 삭제 (세션과 1:1 관계인 경우)
        await self._character_repo.delete(character.id)
