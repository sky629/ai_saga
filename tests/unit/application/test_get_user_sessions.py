"""Unit tests for GetUserSessionsQuery with cursor-based pagination."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from app.common.utils.datetime import get_utc_datetime
from app.game.application.queries.get_user_sessions import (
    GetUserSessionsQuery,
    SessionListItem,
)


class TestGetUserSessionsQuery:
    """GetUserSessionsQuery Unit Test (Cursor-based pagination)"""

    @pytest.fixture
    def mock_db(self):
        """Mock AsyncSession"""
        return AsyncMock()

    @pytest.fixture
    def query(self, mock_db):
        """Query instance"""
        return GetUserSessionsQuery(mock_db)

    async def test_execute_first_page_no_cursor(self, query, mock_db):
        """First page query (no cursor)"""
        user_id = UUID("019c0000-0000-0000-0000-000000000001")

        # Mock: character query
        char_result = MagicMock()
        char_result.fetchall.return_value = [
            (UUID("019c0000-0000-0000-0000-000000000002"),)
        ]

        # Mock: session query
        session_result = MagicMock()
        mock_sessions = [self._create_mock_session(i) for i in range(5)]
        session_result.scalars.return_value.all.return_value = mock_sessions

        mock_db.execute.side_effect = [char_result, session_result]

        # When
        result = await query.execute(user_id=user_id, limit=20, cursor=None)

        # Then
        assert len(result) == 5
        assert all(isinstance(item, SessionListItem) for item in result)
        # DB called 2 times (character + session)
        assert mock_db.execute.call_count == 2

    async def test_execute_with_cursor(self, query, mock_db):
        """Query next page with cursor"""
        user_id = UUID("019c0000-0000-0000-0000-000000000001")
        cursor = UUID("019c0000-0000-0000-0000-000000000005")

        # Mock setup
        char_result = MagicMock()
        char_result.fetchall.return_value = [
            (UUID("019c0000-0000-0000-0000-000000000002"),)
        ]

        cursor_result = MagicMock()
        mock_cursor_session = self._create_mock_session(5)
        cursor_result.scalar_one_or_none.return_value = mock_cursor_session

        session_result = MagicMock()
        mock_sessions = [self._create_mock_session(i) for i in range(6, 10)]
        session_result.scalars.return_value.all.return_value = mock_sessions

        mock_db.execute.side_effect = [
            char_result,
            cursor_result,
            session_result,
        ]

        # When
        result = await query.execute(user_id=user_id, limit=20, cursor=cursor)

        # Then
        assert len(result) == 4
        # DB called 3 times (character + cursor session + next sessions)
        assert mock_db.execute.call_count == 3

    async def test_execute_with_status_filter(self, query, mock_db):
        """Status filtering"""
        user_id = UUID("019c0000-0000-0000-0000-000000000001")

        # Mock setup
        char_result = MagicMock()
        char_result.fetchall.return_value = [
            (UUID("019c0000-0000-0000-0000-000000000002"),)
        ]

        session_result = MagicMock()
        mock_sessions = [
            self._create_mock_session(i, status="active") for i in range(3)
        ]
        session_result.scalars.return_value.all.return_value = mock_sessions

        mock_db.execute.side_effect = [char_result, session_result]

        # When
        result = await query.execute(
            user_id=user_id, limit=20, status_filter="active"
        )

        # Then
        assert len(result) == 3
        assert all(item.status == "active" for item in result)

    async def test_execute_no_characters(self, query, mock_db):
        """User has no characters"""
        user_id = UUID("019c0000-0000-0000-0000-000000000001")

        char_result = MagicMock()
        char_result.fetchall.return_value = []
        mock_db.execute.return_value = char_result

        # When
        result = await query.execute(user_id=user_id, limit=20)

        # Then
        assert result == []

    def _create_mock_session(self, index: int, status: str = "active"):
        """Create mock GameSession"""
        from app.common.utils.id_generator import get_uuid7

        mock_session = MagicMock()
        mock_session.id = get_uuid7()
        mock_session.status = status
        mock_session.turn_count = index
        mock_session.max_turns = 10
        mock_session.started_at = get_utc_datetime()
        mock_session.last_activity_at = get_utc_datetime()
        mock_session.ending_type = None

        # Mock relationships
        mock_session.character = MagicMock()
        mock_session.character.name = f"Character {index}"
        mock_session.scenario = MagicMock()
        mock_session.scenario.name = f"Scenario {index}"

        return mock_session
