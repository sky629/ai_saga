"""GetSessionQuery 단위 테스트."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.game.application.queries import GetSessionQuery


class TestGetSessionQuery:
    """GetSessionQuery 단위 테스트."""

    @pytest.fixture
    def mock_repository(self):
        """Mock GameSessionRepository."""
        return AsyncMock()

    @pytest.fixture
    def query(self, mock_repository):
        """Query 인스턴스."""
        return GetSessionQuery(mock_repository)

    @pytest.mark.asyncio
    async def test_execute_returns_session_when_found_and_authorized(
        self, query, mock_repository
    ):
        """세션이 존재하고 권한이 있으면 반환."""
        session_id = uuid4()
        user_id = uuid4()

        # Mock session with matching user_id
        mock_session = AsyncMock()
        mock_session.user_id = user_id
        mock_repository.get_by_id.return_value = mock_session

        result = await query.execute(session_id, user_id)

        assert result == mock_session
        mock_repository.get_by_id.assert_called_once_with(session_id)

    @pytest.mark.asyncio
    async def test_execute_returns_none_when_not_found(
        self, query, mock_repository
    ):
        """세션이 없으면 None 반환."""
        session_id = uuid4()
        user_id = uuid4()
        mock_repository.get_by_id.return_value = None

        result = await query.execute(session_id, user_id)

        assert result is None
        mock_repository.get_by_id.assert_called_once_with(session_id)

    @pytest.mark.asyncio
    async def test_execute_returns_none_when_unauthorized(
        self, query, mock_repository
    ):
        """다른 사용자의 세션이면 None 반환 (권한 검증)."""
        session_id = uuid4()
        user_id = uuid4()
        other_user_id = uuid4()

        # Mock session with different user_id
        mock_session = AsyncMock()
        mock_session.user_id = other_user_id  # 다른 사용자 소유
        mock_repository.get_by_id.return_value = mock_session

        result = await query.execute(session_id, user_id)

        assert result is None  # 권한 없으면 None
        mock_repository.get_by_id.assert_called_once_with(session_id)
