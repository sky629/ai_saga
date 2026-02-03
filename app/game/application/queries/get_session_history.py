"""Get Session History Query.

게임 세션의 메시지 히스토리를 조회하는 읽기 전용 쿼리.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.game.infrastructure.persistence.models.game_models import GameMessage, GameSession


class MessageHistoryItem(BaseModel):
    """메시지 히스토리 항목 DTO."""
    model_config = {"frozen": True}
    
    id: UUID
    role: str
    content: str
    created_at: datetime
    parsed_response: Optional[dict] = None


class SessionHistoryResult(BaseModel):
    """세션 히스토리 결과 DTO."""
    model_config = {"frozen": True}
    
    session_id: UUID
    turn_count: int
    max_turns: int
    status: str
    current_location: str
    messages: list[MessageHistoryItem]


class GetSessionHistoryQuery:
    """세션 히스토리 조회 쿼리.
    
    CQRS Query: 읽기 전용, 상태 변경 없음.
    """

    def __init__(self, db: AsyncSession):
        self._db = db

    async def execute(
        self,
        session_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> Optional[SessionHistoryResult]:
        """세션 히스토리 조회."""
        # 세션 조회
        session_result = await self._db.execute(
            select(GameSession).where(GameSession.id == session_id)
        )
        session = session_result.scalar_one_or_none()

        if session is None:
            return None

        # 메시지 조회
        messages_result = await self._db.execute(
            select(GameMessage)
            .where(GameMessage.session_id == session_id)
            .order_by(GameMessage.created_at)
            .offset(offset)
            .limit(limit)
        )
        messages = messages_result.scalars().all()

        return SessionHistoryResult(
            session_id=session.id,
            turn_count=session.turn_count,
            max_turns=session.max_turns,
            status=session.status,
            current_location=session.current_location,
            messages=[
                MessageHistoryItem(
                    id=m.id,
                    role=m.role,
                    content=m.content,
                    created_at=m.created_at,
                    parsed_response=m.parsed_response,
                )
                for m in messages
            ],
        )

    async def get_recent_messages(
        self,
        session_id: UUID,
        limit: int = 10,
    ) -> list[MessageHistoryItem]:
        """최근 메시지만 조회."""
        result = await self._db.execute(
            select(GameMessage)
            .where(GameMessage.session_id == session_id)
            .order_by(desc(GameMessage.created_at))
            .limit(limit)
        )
        messages = result.scalars().all()

        # 시간순으로 정렬
        return [
            MessageHistoryItem(
                id=m.id,
                role=m.role,
                content=m.content,
                created_at=m.created_at,
                parsed_response=m.parsed_response,
            )
            for m in reversed(list(messages))
        ]
