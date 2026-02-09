"""Unit tests for GetSessionHistoryQuery with cursor-based pagination."""

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

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

        # Mock: no cache
        mock_redis.get.return_value = None

        # Mock: message query (limit + 1)
        msg_result = MagicMock()
        mock_messages = [self._create_mock_message(i) for i in range(51)]
        msg_result.scalars.return_value.all.return_value = mock_messages

        mock_db.execute.return_value = msg_result

        # When
        messages, next_cursor, has_more = await query.execute_with_cursor(
            session_id=session_id, limit=50, cursor=None
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

        # Mock: no cache
        mock_redis.get.return_value = None

        # Mock: cursor message
        cursor_result = MagicMock()
        mock_cursor_msg = self._create_mock_message(50)
        cursor_result.scalar_one_or_none.return_value = mock_cursor_msg

        # Mock: next messages
        msg_result = MagicMock()
        mock_messages = [self._create_mock_message(i) for i in range(51, 100)]
        msg_result.scalars.return_value.all.return_value = mock_messages

        mock_db.execute.side_effect = [cursor_result, msg_result]

        # When
        messages, next_cursor, has_more = await query.execute_with_cursor(
            session_id=session_id, limit=50, cursor=cursor
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

        # When
        messages, next_cursor, has_more = await query.execute_with_cursor(
            session_id=session_id, limit=50, cursor=cursor
        )

        # Then
        assert len(messages) == 10
        assert has_more is True
        assert next_cursor == UUID("019c0000-0000-0000-0000-000000000060")
        # DB should not be called
        mock_db.execute.assert_not_called()

    async def test_execute_with_cursor_no_more_messages(
        self, query, mock_db, mock_redis
    ):
        """No more messages available"""
        session_id = UUID("019c0000-0000-0000-0000-000000000001")

        # Mock: no cache
        mock_redis.get.return_value = None

        msg_result = MagicMock()
        msg_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = msg_result

        # When
        messages, next_cursor, has_more = await query.execute_with_cursor(
            session_id=session_id, limit=50, cursor=None
        )

        # Then
        assert messages == []
        assert has_more is False
        assert next_cursor is None

    def _create_mock_message(self, index: int):
        """Create mock GameMessage"""
        from app.common.utils.id_generator import get_uuid7

        mock_msg = MagicMock()
        mock_msg.id = get_uuid7()
        mock_msg.role = "user" if index % 2 == 0 else "assistant"
        mock_msg.content = f"Message {index}"
        mock_msg.created_at = get_utc_datetime()
        mock_msg.parsed_response = None

        return mock_msg
