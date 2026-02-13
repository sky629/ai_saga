"""Unit tests for ProcessActionUseCase.

Tests the business logic of action processing with mocked repositories.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.game.application.use_cases.process_action import (
    ProcessActionInput,
    ProcessActionUseCase,
)
from app.game.domain.entities import GameSessionEntity
from app.game.domain.value_objects import SessionStatus


@pytest.mark.asyncio
class TestProcessActionOnCompletedSession:
    """Test ProcessActionUseCase behavior on completed sessions."""

    @pytest.fixture
    def completed_session(self):
        """Create a completed game session entity."""
        session_id = uuid4()
        user_id = uuid4()
        character_id = uuid4()
        scenario_id = uuid4()
        now = datetime.now(timezone.utc)

        session = GameSessionEntity(
            id=session_id,
            user_id=user_id,
            character_id=character_id,
            scenario_id=scenario_id,
            current_location="Forest",
            game_state={},
            status=SessionStatus.COMPLETED,  # Already completed
            turn_count=10,
            max_turns=10,
            ending_type=None,
            started_at=now,
            last_activity_at=now,
        )
        return session

    @pytest.fixture
    def mock_repositories(self, completed_session):
        """Create mocked repositories."""
        session_repo = AsyncMock()
        session_repo.get_by_id.return_value = completed_session

        message_repo = AsyncMock()
        character_repo = AsyncMock()
        llm_service = AsyncMock()
        cache_service = AsyncMock()
        cache_service.get.return_value = None  # No cached response

        embedding_service = AsyncMock()
        embedding_service.generate_embedding.return_value = [
            0.1
        ] * 768  # Mock 768-dim vector

        return {
            "session_repo": session_repo,
            "message_repo": message_repo,
            "character_repo": character_repo,
            "llm_service": llm_service,
            "cache_service": cache_service,
            "embedding_service": embedding_service,
        }

    @pytest.fixture
    def use_case(self, mock_repositories):
        """Create ProcessActionUseCase with mocked dependencies."""
        return ProcessActionUseCase(
            session_repository=mock_repositories["session_repo"],
            message_repository=mock_repositories["message_repo"],
            character_repository=mock_repositories["character_repo"],
            llm_service=mock_repositories["llm_service"],
            cache_service=mock_repositories["cache_service"],
            embedding_service=mock_repositories["embedding_service"],
        )

    async def test_process_action_on_completed_session_raises_value_error(
        self, use_case, completed_session, mock_repositories
    ):
        """완료된 세션에 액션 제출 시 ValueError 발생."""
        input_data = ProcessActionInput(
            session_id=completed_session.id,
            action="북쪽으로 이동",
            idempotency_key="test-key",
        )

        # When & Then: 액션 제출 시 에러 발생
        with pytest.raises(ValueError, match="already completed"):
            await use_case.execute(completed_session.user_id, input_data)

        # Verify: LLM이 호출되지 않았는지 확인 (토큰 절약)
        mock_repositories["llm_service"].generate_response.assert_not_called()

        # Verify: 메시지가 저장되지 않았는지 확인
        mock_repositories["message_repo"].create.assert_not_called()

    async def test_process_action_on_paused_session_raises_value_error(
        self, use_case, completed_session, mock_repositories
    ):
        """일시중지된 세션에 액션 제출 시 ValueError 발생."""
        # Given: PAUSED 상태로 변경
        paused_session = completed_session.model_copy(
            update={"status": SessionStatus.PAUSED}
        )
        mock_repositories["session_repo"].get_by_id.return_value = (
            paused_session
        )

        input_data = ProcessActionInput(
            session_id=paused_session.id,
            action="북쪽으로 이동",
            idempotency_key="test-key",
        )

        # When & Then
        with pytest.raises(ValueError, match="not in active state"):
            await use_case.execute(paused_session.user_id, input_data)

        # Verify: LLM이 호출되지 않았는지 확인
        mock_repositories["llm_service"].generate_response.assert_not_called()
