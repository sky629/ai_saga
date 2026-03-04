"""Get User Sessions Query.

사용자의 게임 세션 목록을 조회하는 읽기 전용 쿼리.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.game.application.ports import (
    GameSessionRepositoryInterface,
    UserSessionReadModel,
)


class SessionListItem(BaseModel):
    """세션 목록 항목 DTO."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    character_name: str
    scenario_name: str
    status: str
    turn_count: int
    max_turns: int
    started_at: datetime
    last_activity_at: datetime
    ending_type: Optional[str] = None
    character: object  # CharacterEntity or dict


class GetUserSessionsQuery:
    """사용자 세션 목록 조회 쿼리.

    CQRS Query: 읽기 전용, 상태 변경 없음.
    """

    def __init__(self, session_repo: GameSessionRepositoryInterface):
        self._session_repo = session_repo

    async def execute(
        self,
        user_id: UUID,
        status_filter: Optional[str] = None,
        limit: int = 20,
        cursor: Optional[UUID] = None,
    ) -> list[SessionListItem]:
        """사용자의 게임 세션 목록 조회."""
        sessions = await self._session_repo.list_by_user(
            user_id=user_id,
            status_filter=status_filter,
            limit=limit,
            cursor=cursor,
        )

        return [self._to_list_item(session) for session in sessions]

    async def get_active_session(
        self, user_id: UUID
    ) -> Optional[SessionListItem]:
        """사용자의 활성 세션 조회."""
        sessions = await self.execute(user_id, status_filter="active", limit=1)
        return sessions[0] if sessions else None

    @staticmethod
    def _to_list_item(session: UserSessionReadModel) -> SessionListItem:
        return SessionListItem(
            id=session.id,
            character_name=session.character_name,
            scenario_name=session.scenario_name,
            status=session.status,
            turn_count=session.turn_count,
            max_turns=session.max_turns,
            started_at=session.started_at,
            last_activity_at=session.last_activity_at,
            ending_type=session.ending_type,
            character=session.character,
        )
