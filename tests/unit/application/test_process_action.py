"""Unit tests for ProcessActionUseCase.

Tests the business logic of action processing with mocked repositories.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
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


@pytest.mark.asyncio
class TestImageGenerationFlag:
    """Test image generation on/off flag and interval logic."""

    @pytest.fixture
    def active_session(self):
        """Create an active game session entity.

        Note: advance_turn() will be called, so turn_count will increase by 1.
        """
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
            status=SessionStatus.ACTIVE,
            turn_count=2,  # advance_turn() 후 3이 됨 (interval=3일 때 이미지 생성)
            max_turns=10,
            ending_type=None,
            started_at=now,
            last_activity_at=now,
        )
        return session

    @pytest.fixture
    def mock_repositories_with_image(self, active_session):
        """Create mocked repositories with image service."""
        session_repo = AsyncMock()
        session_repo.get_by_id.return_value = active_session

        message_repo = AsyncMock()
        message_repo.get_recent_messages.return_value = []
        message_repo.get_similar_messages.return_value = []

        character_repo = AsyncMock()

        llm_service = AsyncMock()
        llm_service.generate_response.return_value = AsyncMock(
            content="You continue your journey through the forest.",
            usage=AsyncMock(total_tokens=50),
        )

        cache_service = AsyncMock()
        cache_service.get.return_value = None  # No cached response

        embedding_service = AsyncMock()
        embedding_service.generate_embedding.return_value = [0.1] * 768

        image_service = AsyncMock()
        image_service.generate_image.return_value = (
            "https://example.com/image.png"
        )

        return {
            "session_repo": session_repo,
            "message_repo": message_repo,
            "character_repo": character_repo,
            "llm_service": llm_service,
            "cache_service": cache_service,
            "embedding_service": embedding_service,
            "image_service": image_service,
        }

    @pytest.fixture
    def use_case_with_image(self, mock_repositories_with_image):
        """Create ProcessActionUseCase with image service."""
        return ProcessActionUseCase(
            session_repository=mock_repositories_with_image["session_repo"],
            message_repository=mock_repositories_with_image["message_repo"],
            character_repository=mock_repositories_with_image[
                "character_repo"
            ],
            llm_service=mock_repositories_with_image["llm_service"],
            cache_service=mock_repositories_with_image["cache_service"],
            embedding_service=mock_repositories_with_image[
                "embedding_service"
            ],
            image_service=mock_repositories_with_image["image_service"],
        )

    @patch("config.settings.settings")
    async def test_image_generation_disabled(
        self,
        mock_settings,
        use_case_with_image,
        active_session,
        mock_repositories_with_image,
    ):
        """IMAGE_GENERATION_ENABLED=false일 때 이미지 생성 안 됨."""
        # Given: 이미지 생성 비활성화
        mock_settings.image_generation_enabled = False
        mock_settings.image_generation_interval = 3

        input_data = ProcessActionInput(
            session_id=active_session.id,
            action="북쪽으로 이동",
            idempotency_key="test-key-1",
        )

        # When
        await use_case_with_image.execute(active_session.user_id, input_data)

        # Then: 이미지 서비스가 호출되지 않았는지 확인
        mock_repositories_with_image[
            "image_service"
        ].generate_image.assert_not_called()

    @patch("config.settings.settings")
    async def test_image_generation_enabled_with_interval_3(
        self,
        mock_settings,
        use_case_with_image,
        active_session,
        mock_repositories_with_image,
    ):
        """IMAGE_GENERATION_ENABLED=true, INTERVAL=3일 때 3턴마다 생성."""
        # Given: 이미지 생성 활성화, 3턴마다 생성
        mock_settings.image_generation_enabled = True
        mock_settings.image_generation_interval = 3

        # Turn 2 (advance_turn() 후 3이 됨 - should generate)
        active_session = active_session.model_copy(update={"turn_count": 2})
        mock_repositories_with_image["session_repo"].get_by_id.return_value = (
            active_session
        )

        input_data = ProcessActionInput(
            session_id=active_session.id,
            action="북쪽으로 이동",
            idempotency_key="test-key-2",
        )

        # When
        await use_case_with_image.execute(active_session.user_id, input_data)

        # Then: 이미지 서비스가 호출되었는지 확인
        mock_repositories_with_image[
            "image_service"
        ].generate_image.assert_called_once()

    @patch("config.settings.settings")
    async def test_image_generation_enabled_with_interval_0_every_turn(
        self,
        mock_settings,
        use_case_with_image,
        active_session,
        mock_repositories_with_image,
    ):
        """IMAGE_GENERATION_ENABLED=true, INTERVAL=0일 때 매 턴마다 생성."""
        # Given: 이미지 생성 활성화, 매 턴마다 생성
        mock_settings.image_generation_enabled = True
        mock_settings.image_generation_interval = 0

        # Turn 0 (advance_turn() 후 1이 됨 - should generate every turn)
        active_session = active_session.model_copy(update={"turn_count": 0})
        mock_repositories_with_image["session_repo"].get_by_id.return_value = (
            active_session
        )

        input_data = ProcessActionInput(
            session_id=active_session.id,
            action="북쪽으로 이동",
            idempotency_key="test-key-3",
        )

        # When
        await use_case_with_image.execute(active_session.user_id, input_data)

        # Then: 이미지 서비스가 호출되었는지 확인
        mock_repositories_with_image[
            "image_service"
        ].generate_image.assert_called_once()

    @patch("config.settings.settings")
    async def test_image_generation_not_on_non_interval_turn(
        self,
        mock_settings,
        use_case_with_image,
        active_session,
        mock_repositories_with_image,
    ):
        """INTERVAL=3일 때 2턴째에는 이미지 생성 안 됨."""
        # Given: 이미지 생성 활성화, 3턴마다 생성
        mock_settings.image_generation_enabled = True
        mock_settings.image_generation_interval = 3

        # Turn 1 (advance_turn() 후 2가 됨 - should NOT generate)
        active_session = active_session.model_copy(update={"turn_count": 1})
        mock_repositories_with_image["session_repo"].get_by_id.return_value = (
            active_session
        )

        input_data = ProcessActionInput(
            session_id=active_session.id,
            action="북쪽으로 이동",
            idempotency_key="test-key-4",
        )

        # When
        await use_case_with_image.execute(active_session.user_id, input_data)

        # Then: 이미지 서비스가 호출되지 않았는지 확인
        mock_repositories_with_image[
            "image_service"
        ].generate_image.assert_not_called()
