"""Unit tests for GetSessionHistoryQuery with cursor-based pagination."""

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from app.common.exception import Forbidden
from app.common.utils.datetime import get_utc_datetime
from app.game.application.queries.get_session_history import (
    GetSessionHistoryQuery,
)


class TestGetSessionHistoryQuery:
    """GetSessionHistoryQuery Unit Test (Cursor-based pagination)"""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_redis(self):
        return AsyncMock()

    @pytest.fixture
    def query(self, mock_db, mock_redis):
        return GetSessionHistoryQuery(mock_db, mock_redis)

    async def test_execute_with_cursor_first_page(
        self, query, mock_db, mock_redis
    ):
        """First page query (latest messages first)"""
        session_id = UUID("019c0000-0000-0000-0000-000000000001")
        user_id = UUID("019c0000-0000-0000-0000-000000000999")

        # Mock: no cache
        mock_redis.get.return_value = None

        # Mock: ownership check session
        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = (
            self._create_mock_session(session_id, user_id)
        )

        # Mock: message query (limit + 1)
        msg_result = MagicMock()
        mock_messages = [self._create_mock_message(i) for i in range(51)]
        msg_result.scalars.return_value.all.return_value = mock_messages

        mock_db.execute.side_effect = [session_result, msg_result]

        # When
        messages, next_cursor, has_more = await query.execute_with_cursor(
            session_id=session_id, user_id=user_id, limit=50, cursor=None
        )

        # Then
        assert len(messages) == 50  # Only limit returned
        assert has_more is True
        assert next_cursor is not None
        assert next_cursor == mock_messages[49].id
        # No cache for latest messages
        mock_redis.get.assert_not_called()

    async def test_execute_with_cursor_next_page(
        self, query, mock_db, mock_redis
    ):
        """Next page query with cursor"""
        session_id = UUID("019c0000-0000-0000-0000-000000000001")
        cursor = UUID("019c0000-0000-0000-0000-000000000050")
        user_id = UUID("019c0000-0000-0000-0000-000000000999")

        # Mock: no cache
        mock_redis.get.return_value = None

        # Mock: ownership check session
        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = (
            self._create_mock_session(session_id, user_id)
        )

        # Mock: cursor message
        cursor_result = MagicMock()
        mock_cursor_msg = self._create_mock_message(50)
        cursor_result.scalar_one_or_none.return_value = mock_cursor_msg

        # Mock: next messages
        msg_result = MagicMock()
        mock_messages = [self._create_mock_message(i) for i in range(51, 100)]
        msg_result.scalars.return_value.all.return_value = mock_messages

        mock_db.execute.side_effect = [
            session_result,
            cursor_result,
            msg_result,
        ]

        # When
        messages, next_cursor, has_more = await query.execute_with_cursor(
            session_id=session_id, user_id=user_id, limit=50, cursor=cursor
        )

        # Then
        assert len(messages) == 49  # Less than limit (no more)
        assert has_more is False
        assert next_cursor is None
        # Cache should be checked for historical messages
        mock_redis.get.assert_called_once()

    async def test_execute_with_cursor_cache_hit(
        self, query, mock_db, mock_redis
    ):
        """Cache hit for historical messages"""
        import rapidjson

        session_id = UUID("019c0000-0000-0000-0000-000000000001")
        cursor = UUID("019c0000-0000-0000-0000-000000000050")
        user_id = UUID("019c0000-0000-0000-0000-000000000999")

        # Mock: cache hit
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

        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = (
            self._create_mock_session(session_id, user_id)
        )
        mock_db.execute.return_value = session_result

        # When
        messages, next_cursor, has_more = await query.execute_with_cursor(
            session_id=session_id, user_id=user_id, limit=50, cursor=cursor
        )

        # Then
        assert len(messages) == 10
        assert has_more is True
        assert next_cursor == UUID("019c0000-0000-0000-0000-000000000060")
        # Ownership check query 1회만 호출됨
        assert mock_db.execute.call_count == 1

    async def test_execute_with_cursor_no_more_messages(
        self, query, mock_db, mock_redis
    ):
        """No more messages available"""
        session_id = UUID("019c0000-0000-0000-0000-000000000001")
        user_id = UUID("019c0000-0000-0000-0000-000000000999")

        # Mock: no cache
        mock_redis.get.return_value = None

        # Mock: ownership check session
        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = (
            self._create_mock_session(session_id, user_id)
        )

        msg_result = MagicMock()
        msg_result.scalars.return_value.all.return_value = []
        mock_db.execute.side_effect = [session_result, msg_result]

        # When
        messages, next_cursor, has_more = await query.execute_with_cursor(
            session_id=session_id, user_id=user_id, limit=50, cursor=None
        )

        # Then
        assert messages == []
        assert has_more is False
        assert next_cursor is None

    async def test_execute_with_cursor_forbidden_when_not_owner(
        self, query, mock_db, mock_redis
    ):
        session_id = UUID("019c0000-0000-0000-0000-000000000001")
        owner_id = UUID("019c0000-0000-0000-0000-000000000111")
        requester_id = UUID("019c0000-0000-0000-0000-000000000999")

        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = (
            self._create_mock_session(session_id, owner_id)
        )
        mock_db.execute.return_value = session_result

        with pytest.raises(Forbidden):
            await query.execute_with_cursor(
                session_id=session_id,
                user_id=requester_id,
                limit=50,
                cursor=None,
            )

    def _create_mock_message(self, index: int):
        """Create mock GameMessage"""
        from app.common.utils.id_generator import get_uuid7

        mock_msg = MagicMock()
        mock_msg.id = get_uuid7()
        mock_msg.role = "user" if index % 2 == 0 else "assistant"
        mock_msg.content = f"Message {index}"
        mock_msg.created_at = get_utc_datetime()
        mock_msg.parsed_response = None
        mock_msg.image_url = None

        return mock_msg

    def _create_mock_session(self, session_id: UUID, user_id: UUID):
        mock_session = MagicMock()
        mock_session.id = session_id
        mock_session.user_id = user_id
        return mock_session
