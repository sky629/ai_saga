"""게임 세션 단건 조회 쿼리."""

from typing import Optional
from uuid import UUID

from app.game.application.ports import GameSessionRepositoryInterface
from app.game.domain.entities import GameSessionEntity


class GetSessionQuery:
    """게임 세션 단건 조회 쿼리.

    Repository의 get_by_id를 호출하고, 권한을 검증합니다.
    다른 사용자의 세션은 조회할 수 없습니다.
    """

    def __init__(self, repository: GameSessionRepositoryInterface):
        self._repository = repository

    async def execute(
        self, session_id: UUID, user_id: UUID
    ) -> Optional[GameSessionEntity]:
        """세션 ID로 세션 조회 (권한 검증 포함).

        Args:
            session_id: 조회할 세션 ID
            user_id: 현재 로그인한 사용자 ID (권한 검증용)

        Returns:
            GameSessionEntity or None
            - 세션이 없으면 None
            - 세션이 다른 사용자 소유면 None (권한 없음)
        """
        session = await self._repository.get_by_id(session_id)

        # 권한 검증: 세션 소유자가 현재 사용자인지 확인
        if session is None:
            return None

        if session.user_id != user_id:
            return None  # 권한 없으면 404처럼 처리

        return session
