"""Get User Sessions Query.

사용자의 게임 세션 목록을 조회하는 읽기 전용 쿼리.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.game.infrastructure.persistence.models.game_models import Character, GameSession


class SessionListItem(BaseModel):
    """세션 목록 항목 DTO."""
    model_config = {"frozen": True}
    
    id: UUID
    character_name: str
    scenario_name: str
    status: str
    turn_count: int
    max_turns: int
    started_at: datetime
    last_activity_at: datetime
    ending_type: Optional[str] = None


class GetUserSessionsQuery:
    """사용자 세션 목록 조회 쿼리.
    
    CQRS Query: 읽기 전용, 상태 변경 없음.
    """

    def __init__(self, db: AsyncSession):
        self._db = db

    async def execute(
        self,
        user_id: UUID,
        status_filter: Optional[str] = None,
        limit: int = 20,
    ) -> list[SessionListItem]:
        """사용자의 게임 세션 목록 조회."""
        # 사용자의 캐릭터 ID 조회
        char_result = await self._db.execute(
            select(Character.id).where(Character.user_id == user_id)
        )
        character_ids = [row[0] for row in char_result.fetchall()]

        if not character_ids:
            return []

        # 세션 조회
        query = (
            select(GameSession)
            .options(
                selectinload(GameSession.character),
                selectinload(GameSession.scenario),
            )
            .where(GameSession.character_id.in_(character_ids))
            .order_by(GameSession.last_activity_at.desc())
            .limit(limit)
        )

        if status_filter:
            query = query.where(GameSession.status == status_filter)

        result = await self._db.execute(query)
        sessions = result.scalars().all()

        return [
            SessionListItem(
                id=s.id,
                character_name=s.character.name,
                scenario_name=s.scenario.name,
                status=s.status,
                turn_count=s.turn_count,
                max_turns=s.max_turns,
                started_at=s.started_at,
                last_activity_at=s.last_activity_at,
                ending_type=s.ending_type,
            )
            for s in sessions
        ]

    async def get_active_session(self, user_id: UUID) -> Optional[SessionListItem]:
        """사용자의 활성 세션 조회."""
        sessions = await self.execute(user_id, status_filter="active", limit=1)
        return sessions[0] if sessions else None
