"""Get Session History Query.

게임 세션의 메시지 히스토리를 조회하는 읽기 전용 쿼리.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

import rapidjson
from pydantic import BaseModel, ConfigDict
from redis.asyncio import Redis
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.game.infrastructure.persistence.models.game_models import (
    GameMessage,
    GameSession,
)


class MessageHistoryItem(BaseModel):
    """메시지 히스토리 항목 DTO."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    role: str
    content: str
    created_at: datetime
    parsed_response: Optional[dict] = None
    image_url: Optional[str] = None


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

    def __init__(self, db: AsyncSession, redis: Optional[Redis] = None):
        self._db = db
        self._redis = redis

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
                    image_url=m.image_url,
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
                image_url=m.image_url,
            )
            for m in reversed(list(messages))
        ]

    async def execute_with_cursor(
        self,
        session_id: UUID,
        limit: int = 50,
        cursor: Optional[UUID] = None,
    ) -> tuple[list[MessageHistoryItem], Optional[UUID], bool]:
        """Cursor 기반 메시지 히스토리 조회 with Redis 캐싱.

        캐싱 전략:
        - cursor=None (최신 메시지): 캐시 우회, 항상 DB 조회
        - cursor 있음 (과거 메시지): Redis 캐시 사용 (불변 데이터)

        Returns:
            (messages, next_cursor, has_more)
        """
        # 최신 메시지 조회 시 캐시 우회
        if cursor is None or self._redis is None:
            return await self._fetch_from_db(session_id, limit, cursor)

        # 과거 메시지 조회 시 캐시 사용
        cache_key = (
            f"session:{session_id}:messages:cursor:{cursor}:limit:{limit}"
        )

        # 1. 캐시 조회
        cached = await self._redis.get(cache_key)
        if cached:
            data = rapidjson.loads(cached)
            return (
                [MessageHistoryItem(**item) for item in data["messages"]],
                UUID(data["next_cursor"]) if data["next_cursor"] else None,
                data["has_more"],
            )

        # 2. 캐시 미스 → DB 조회
        messages, next_cursor, has_more = await self._fetch_from_db(
            session_id, limit, cursor
        )

        # 3. 과거 메시지는 불변 → 캐시 저장 (1시간)
        cache_data = {
            "messages": [msg.model_dump(mode="json") for msg in messages],
            "next_cursor": str(next_cursor) if next_cursor else None,
            "has_more": has_more,
        }
        await self._redis.set(
            cache_key,
            rapidjson.dumps(cache_data),
            ex=60 * 60,  # 1시간
        )

        return messages, next_cursor, has_more

    async def _fetch_from_db(
        self,
        session_id: UUID,
        limit: int,
        cursor: Optional[UUID],
    ) -> tuple[list[MessageHistoryItem], Optional[UUID], bool]:
        """DB에서 메시지 조회 (실제 쿼리 로직)."""
        # 메시지 조회 (최신 순, cursor보다 오래된 것만)
        query = (
            select(GameMessage)
            .where(GameMessage.session_id == session_id)
            .order_by(GameMessage.created_at.desc(), GameMessage.id.desc())
        )

        # Cursor 필터링
        if cursor:
            cursor_msg = await self._db.execute(
                select(GameMessage).where(GameMessage.id == cursor)
            )
            cursor_obj = cursor_msg.scalar_one_or_none()
            if cursor_obj:
                query = query.where(
                    (GameMessage.created_at < cursor_obj.created_at)
                    | (
                        (GameMessage.created_at == cursor_obj.created_at)
                        & (GameMessage.id < cursor)
                    )
                )

        query = query.limit(limit + 1)
        result = await self._db.execute(query)
        messages = result.scalars().all()

        # has_more 확인
        has_more = len(messages) > limit
        if has_more:
            messages = messages[:limit]

        # next_cursor 계산
        next_cursor = messages[-1].id if messages and has_more else None

        # DTO 변환
        items = [
            MessageHistoryItem(
                id=m.id,
                role=m.role,
                content=m.content,
                created_at=m.created_at,
                parsed_response=m.parsed_response,
                image_url=m.image_url,
            )
            for m in messages
        ]

        return items, next_cursor, has_more
