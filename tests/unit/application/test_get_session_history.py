"""Unit tests for GetSessionHistoryQuery with repository ports."""

from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from app.common.exception import Forbidden
from app.common.utils.datetime import get_utc_datetime
from app.common.utils.id_generator import get_uuid7
from app.game.application.queries.get_session_history import (
    GetSessionHistoryQuery,
)
from app.game.domain.entities import GameMessageEntity, GameSessionEntity
from app.game.domain.value_objects import MessageRole, SessionStatus


class TestGetSessionHistoryQuery:
    """GetSessionHistoryQuery Unit Test."""

    @pytest.fixture
    def mock_session_repo(self):
        return AsyncMock()

    @pytest.fixture
    def mock_message_repo(self):
        return AsyncMock()

    @pytest.fixture
    def mock_redis(self):
        return AsyncMock()

    @pytest.fixture
    def query(self, mock_session_repo, mock_message_repo, mock_redis):
        return GetSessionHistoryQuery(
            session_repo=mock_session_repo,
            message_repo=mock_message_repo,
            redis=mock_redis,
        )

    async def test_execute_with_cursor_first_page(
        self, query, mock_session_repo, mock_message_repo, mock_redis
    ):
        """First page query (latest messages first)."""
        session_id = UUID("019c0000-0000-0000-0000-000000000001")
        user_id = UUID("019c0000-0000-0000-0000-000000000999")

        mock_redis.get.return_value = None

        mock_messages = [self._create_mock_message(i) for i in range(51)]
        mock_session_repo.get_by_id.return_value = self._create_mock_session(
            session_id,
            user_id,
        )
        mock_message_repo.get_messages_with_cursor.return_value = (
            mock_messages[:50],
            mock_messages[49].id,
            True,
        )

        messages, next_cursor, has_more = await query.execute_with_cursor(
            session_id=session_id, user_id=user_id, limit=50, cursor=None
        )

        assert len(messages) == 50
        assert has_more is True
        assert next_cursor == mock_messages[49].id
        mock_redis.get.assert_not_called()

    async def test_execute_with_cursor_next_page(
        self, query, mock_session_repo, mock_message_repo, mock_redis
    ):
        """Next page query with cursor."""
        session_id = UUID("019c0000-0000-0000-0000-000000000001")
        cursor = UUID("019c0000-0000-0000-0000-000000000050")
        user_id = UUID("019c0000-0000-0000-0000-000000000999")

        mock_redis.get.return_value = None

        mock_messages = [self._create_mock_message(i) for i in range(51, 100)]
        mock_session_repo.get_by_id.return_value = self._create_mock_session(
            session_id,
            user_id,
        )
        mock_message_repo.get_messages_with_cursor.return_value = (
            mock_messages,
            None,
            False,
        )

        messages, next_cursor, has_more = await query.execute_with_cursor(
            session_id=session_id, user_id=user_id, limit=50, cursor=cursor
        )

        assert len(messages) == 49
        assert has_more is False
        assert next_cursor is None
        mock_redis.get.assert_called_once()

    async def test_execute_with_cursor_cache_hit(
        self, query, mock_session_repo, mock_message_repo, mock_redis
    ):
        """Cache hit for historical messages."""
        import rapidjson

        session_id = UUID("019c0000-0000-0000-0000-000000000001")
        cursor = UUID("019c0000-0000-0000-0000-000000000050")
        user_id = UUID("019c0000-0000-0000-0000-000000000999")

        cached_data = {
            "messages": [
                {
                    "id": str(
                        UUID("019c0000-0000-0000-0000-00000000006" + str(i))
                    ),
                    "role": "user" if i % 2 == 0 else "assistant",
                    "content": f"Message {i}",
                    "created_at": get_utc_datetime().isoformat(),
                    "parsed_response": None,
                }
                for i in range(10)
            ],
            "next_cursor": str(UUID("019c0000-0000-0000-0000-000000000060")),
            "has_more": True,
        }
        mock_redis.get.return_value = rapidjson.dumps(cached_data)
        mock_session_repo.get_by_id.return_value = self._create_mock_session(
            session_id,
            user_id,
        )

        messages, next_cursor, has_more = await query.execute_with_cursor(
            session_id=session_id, user_id=user_id, limit=50, cursor=cursor
        )

        assert len(messages) == 10
        assert has_more is True
        assert next_cursor == UUID("019c0000-0000-0000-0000-000000000060")
        mock_message_repo.get_messages_with_cursor.assert_not_called()

    async def test_execute_with_cursor_no_more_messages(
        self, query, mock_session_repo, mock_message_repo, mock_redis
    ):
        """No more messages available."""
        session_id = UUID("019c0000-0000-0000-0000-000000000001")
        user_id = UUID("019c0000-0000-0000-0000-000000000999")

        mock_redis.get.return_value = None

        mock_session_repo.get_by_id.return_value = self._create_mock_session(
            session_id,
            user_id,
        )
        mock_message_repo.get_messages_with_cursor.return_value = (
            [],
            None,
            False,
        )

        messages, next_cursor, has_more = await query.execute_with_cursor(
            session_id=session_id, user_id=user_id, limit=50, cursor=None
        )

        assert messages == []
        assert has_more is False
        assert next_cursor is None

    async def test_execute_with_cursor_forbidden_when_not_owner(
        self, query, mock_session_repo, mock_message_repo, mock_redis
    ):
        session_id = UUID("019c0000-0000-0000-0000-000000000001")
        owner_id = UUID("019c0000-0000-0000-0000-000000000111")
        requester_id = UUID("019c0000-0000-0000-0000-000000000999")

        mock_session_repo.get_by_id.return_value = self._create_mock_session(
            session_id,
            owner_id,
        )

        with pytest.raises(Forbidden):
            await query.execute_with_cursor(
                session_id=session_id,
                user_id=requester_id,
                limit=50,
                cursor=None,
            )

    @staticmethod
    def _create_mock_message(index: int) -> GameMessageEntity:
        return GameMessageEntity(
            id=get_uuid7(),
            session_id=get_uuid7(),
            role=MessageRole.USER if index % 2 == 0 else MessageRole.ASSISTANT,
            content=f"Message {index}",
            parsed_response=None,
            image_url=None,
            created_at=get_utc_datetime(),
        )

    @staticmethod
    def _create_mock_session(
        session_id: UUID, user_id: UUID
    ) -> GameSessionEntity:
        now = get_utc_datetime()
        return GameSessionEntity(
            id=session_id,
            user_id=user_id,
            character_id=get_uuid7(),
            scenario_id=get_uuid7(),
            current_location="start",
            game_state={},
            status=SessionStatus.ACTIVE,
            turn_count=1,
            max_turns=30,
            ending_type=None,
            started_at=now,
            ended_at=None,
            last_activity_at=now,
        )
