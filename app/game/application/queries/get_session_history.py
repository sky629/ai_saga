"""Get Session History Query.

게임 세션의 메시지 히스토리를 조회하는 읽기 전용 쿼리.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

import rapidjson
from pydantic import BaseModel, ConfigDict
from redis.asyncio import Redis

from app.common.exception import Forbidden
from app.game.application.ports import (
    GameMessageRepositoryInterface,
    GameSessionRepositoryInterface,
)
from app.game.domain.entities import GameMessageEntity


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

    def __init__(
        self,
        session_repo: GameSessionRepositoryInterface,
        message_repo: GameMessageRepositoryInterface,
        redis: Optional[Redis] = None,
    ):
        self._session_repo = session_repo
        self._message_repo = message_repo
        self._redis = redis

    async def execute(
        self,
        session_id: UUID,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> Optional[SessionHistoryResult]:
        """세션 히스토리 조회."""
        session = await self._session_repo.get_by_id(session_id)

        if session is None:
            return None
        if session.user_id != user_id:
            raise Forbidden(message="해당 세션에 접근할 권한이 없습니다.")

        messages = await self._message_repo.get_messages(
            session_id=session_id,
            limit=limit,
            offset=offset,
        )

        return SessionHistoryResult(
            session_id=session.id,
            turn_count=session.turn_count,
            max_turns=session.max_turns,
            status=session.status.value,
            current_location=session.current_location,
            messages=[self._to_message_item(message) for message in messages],
        )

    async def get_recent_messages(
        self,
        session_id: UUID,
        limit: int = 10,
    ) -> list[MessageHistoryItem]:
        """최근 메시지만 조회."""
        messages = await self._message_repo.get_recent_messages(
            session_id=session_id,
            limit=limit,
        )
        return [self._to_message_item(message) for message in messages]

    async def execute_with_cursor(
        self,
        session_id: UUID,
        user_id: UUID,
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
        await self._validate_session_ownership(session_id, user_id)

        # 최신 메시지 조회 시 캐시 우회
        if cursor is None or self._redis is None:
            return await self._read_with_cursor(session_id, limit, cursor)

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
        messages, next_cursor, has_more = await self._read_with_cursor(
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

    async def _validate_session_ownership(
        self, session_id: UUID, user_id: UUID
    ) -> None:
        session = await self._session_repo.get_by_id(session_id)
        if session is None:
            return
        if session.user_id != user_id:
            raise Forbidden(message="해당 세션에 접근할 권한이 없습니다.")

    async def _read_with_cursor(
        self,
        session_id: UUID,
        limit: int,
        cursor: Optional[UUID],
    ) -> tuple[list[MessageHistoryItem], Optional[UUID], bool]:
        messages, next_cursor, has_more = (
            await self._message_repo.get_messages_with_cursor(
                session_id=session_id,
                limit=limit,
                cursor=cursor,
            )
        )
        return (
            [self._to_message_item(message) for message in messages],
            next_cursor,
            has_more,
        )

    @staticmethod
    def _to_message_item(message: GameMessageEntity) -> MessageHistoryItem:
        return MessageHistoryItem(
            id=message.id,
            role=message.role.value,
            content=message.content,
            created_at=message.created_at,
            parsed_response=message.parsed_response,
            image_url=message.image_url,
        )
