"""Unit tests for GetUserSessionsQuery with query port."""

from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from app.common.utils.datetime import get_utc_datetime
from app.game.application.ports import UserSessionReadModel
from app.game.application.queries.get_user_sessions import (
    GetUserSessionsQuery,
    SessionListItem,
)


class TestGetUserSessionsQuery:
    """GetUserSessionsQuery Unit Test."""

    @pytest.fixture
    def mock_session_repo(self):
        """Mock session repository."""
        return AsyncMock()

    @pytest.fixture
    def query(self, mock_session_repo):
        """Query instance"""
        return GetUserSessionsQuery(mock_session_repo)

    async def test_execute_first_page_no_cursor(
        self, query, mock_session_repo
    ):
        """First page query."""
        user_id = UUID("019c0000-0000-0000-0000-000000000001")
        mock_sessions = [self._create_mock_session(i) for i in range(5)]
        mock_session_repo.list_by_user.return_value = mock_sessions

        # When
        result = await query.execute(user_id=user_id, limit=20, cursor=None)

        # Then
        assert len(result) == 5
        assert all(isinstance(item, SessionListItem) for item in result)
        mock_session_repo.list_by_user.assert_awaited_once_with(
            user_id=user_id,
            status_filter=None,
            limit=20,
            cursor=None,
        )

    async def test_execute_with_cursor(self, query, mock_session_repo):
        """Query next page with cursor"""
        user_id = UUID("019c0000-0000-0000-0000-000000000001")
        cursor = UUID("019c0000-0000-0000-0000-000000000005")
        mock_sessions = [self._create_mock_session(i) for i in range(6, 10)]
        mock_session_repo.list_by_user.return_value = mock_sessions

        # When
        result = await query.execute(user_id=user_id, limit=20, cursor=cursor)

        # Then
        assert len(result) == 4
        mock_session_repo.list_by_user.assert_awaited_once_with(
            user_id=user_id,
            status_filter=None,
            limit=20,
            cursor=cursor,
        )

    async def test_execute_with_status_filter(self, query, mock_session_repo):
        """Status filtering"""
        user_id = UUID("019c0000-0000-0000-0000-000000000001")
        mock_sessions = [
            self._create_mock_session(i, status="active") for i in range(3)
        ]
        mock_session_repo.list_by_user.return_value = mock_sessions

        # When
        result = await query.execute(
            user_id=user_id, limit=20, status_filter="active"
        )

        # Then
        assert len(result) == 3
        assert all(item.status == "active" for item in result)

    async def test_execute_no_characters(self, query, mock_session_repo):
        """User has no characters"""
        user_id = UUID("019c0000-0000-0000-0000-000000000001")
        mock_session_repo.list_by_user.return_value = []

        # When
        result = await query.execute(user_id=user_id, limit=20)

        # Then
        assert result == []

    def _create_mock_session(self, index: int, status: str = "active"):
        """Create mock UserSessionReadModel."""
        from app.common.utils.id_generator import get_uuid7

        character = AsyncMock()
        character.id = get_uuid7()
        character.name = f"Character {index}"

        return UserSessionReadModel(
            id=get_uuid7(),
            character_name=f"Character {index}",
            scenario_name=f"Scenario {index}",
            status=status,
            turn_count=index,
            max_turns=10,
            started_at=get_utc_datetime(),
            last_activity_at=get_utc_datetime(),
            ending_type=None,
            character=character,
        )
