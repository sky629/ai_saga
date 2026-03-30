"""게임 세션 단건 조회 쿼리."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.game.application.ports import (
    GameMessageRepositoryInterface,
    GameSessionRepositoryInterface,
)
from app.game.domain.entities import GameSessionEntity


class SessionDetailResult(BaseModel):
    """게임 세션 상세 조회 결과 DTO."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    character_id: UUID
    scenario_id: UUID
    current_location: str
    game_state: dict
    status: str
    turn_count: int
    max_turns: int
    ending_type: Optional[str] = None
    started_at: datetime
    last_activity_at: datetime
    image_url: Optional[str] = None


class GetSessionQuery:
    """게임 세션 단건 조회 쿼리.

    Repository의 get_by_id를 호출하고, 권한을 검증합니다.
    다른 사용자의 세션은 조회할 수 없습니다.
    """

    def __init__(
        self,
        repository: GameSessionRepositoryInterface,
        message_repository: GameMessageRepositoryInterface,
    ):
        self._repository = repository
        self._message_repository = message_repository

    async def execute(
        self, session_id: UUID, user_id: UUID
    ) -> Optional[SessionDetailResult]:
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

        illustrated_message = (
            await self._message_repository.get_first_illustrated_message(
                session_id
            )
        )

        return self._to_result(
            session=session,
            image_url=(
                illustrated_message.image_url if illustrated_message else None
            ),
        )

    @staticmethod
    def _to_result(
        session: GameSessionEntity, image_url: Optional[str]
    ) -> SessionDetailResult:
        return SessionDetailResult(
            id=session.id,
            character_id=session.character_id,
            scenario_id=session.scenario_id,
            current_location=session.current_location,
            game_state=session.game_state,
            status=session.status.value,
            turn_count=session.turn_count,
            max_turns=session.max_turns,
            ending_type=(
                session.ending_type.value if session.ending_type else None
            ),
            started_at=session.started_at,
            last_activity_at=session.last_activity_at,
            image_url=image_url,
        )
