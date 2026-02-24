"""Unit tests for ProcessActionUseCase.

Tests the business logic of action processing with mocked repositories.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.game.application.use_cases.process_action import (
    ProcessActionInput,
    ProcessActionUseCase,
)
from app.game.domain.entities import GameSessionEntity
from app.game.domain.value_objects import SessionStatus
from app.game.presentation.routes.schemas.response import (
    GameActionResponse,
    GameEndingResponse,
)


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
        scenario_repo = AsyncMock()
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
            "scenario_repo": scenario_repo,
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
            scenario_repository=mock_repositories["scenario_repo"],
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
class TestGameEndingDetection:
    """Test game ending detection via is_ending flag."""

    @pytest.fixture
    def base_session(self):
        """Base active session factory."""
        now = datetime.now(timezone.utc)

        def make_session(turn_count: int, max_turns: int = 10):
            return GameSessionEntity(
                id=uuid4(),
                user_id=uuid4(),
                character_id=uuid4(),
                scenario_id=uuid4(),
                current_location="Forest",
                game_state={},
                status=SessionStatus.ACTIVE,
                turn_count=turn_count,
                max_turns=max_turns,
                ending_type=None,
                started_at=now,
                last_activity_at=now,
            )

        return make_session

    def _make_repos(self, session):
        """공통 mock repository 생성."""
        session_repo = AsyncMock()
        session_repo.get_by_id.return_value = session

        message_repo = AsyncMock()
        message_repo.get_recent_messages.return_value = []
        message_repo.get_similar_messages.return_value = []

        character_repo = AsyncMock()
        character_mock = MagicMock()
        character_mock.name = "테스트 캐릭터"
        character_repo.get_by_id.return_value = character_mock

        scenario_repo = AsyncMock()

        llm_service = AsyncMock()
        llm_service.generate_response.return_value = AsyncMock(
            content="You continue your journey.",
            usage=AsyncMock(total_tokens=50),
        )

        cache_service = AsyncMock()
        cache_service.get.return_value = None

        embedding_service = AsyncMock()
        embedding_service.generate_embedding.return_value = [0.1] * 768

        return {
            "session_repo": session_repo,
            "message_repo": message_repo,
            "character_repo": character_repo,
            "scenario_repo": scenario_repo,
            "llm_service": llm_service,
            "cache_service": cache_service,
            "embedding_service": embedding_service,
        }

    def _make_use_case(self, repos):
        return ProcessActionUseCase(
            session_repository=repos["session_repo"],
            message_repository=repos["message_repo"],
            character_repository=repos["character_repo"],
            scenario_repository=repos["scenario_repo"],
            llm_service=repos["llm_service"],
            cache_service=repos["cache_service"],
            embedding_service=repos["embedding_service"],
        )

    @patch("config.settings.settings")
    async def test_second_to_last_turn_has_is_ending_true(self, base_session):
        """Turn 9 (max=10): is_ending=True 경고 - 다음 턴이 마지막임을 알림."""
        # Given: turn_count=8, advance_turn() 후 9가 됨 → remaining_turns=1
        session = base_session(turn_count=8, max_turns=10)
        repos = self._make_repos(session)
        use_case = self._make_use_case(repos)

        input_data = ProcessActionInput(
            session_id=session.id,
            action="북쪽으로 이동",
            idempotency_key="ending-warn-key",
        )

        # When
        result = await use_case.execute(session.user_id, input_data)

        # Then: GameActionResponse이며 is_ending=True
        assert isinstance(result.response, GameActionResponse)
        assert result.response.is_ending is True
        assert result.response.turn_count == 9
        assert result.response.max_turns == 10

    @patch("config.settings.settings")
    async def test_normal_turn_has_is_ending_false(self, base_session):
        """Turn 5 (max=10): is_ending=False - 아직 여러 턴 남음."""
        # Given: turn_count=4, advance_turn() 후 5가 됨 → remaining_turns=5
        session = base_session(turn_count=4, max_turns=10)
        repos = self._make_repos(session)
        use_case = self._make_use_case(repos)

        input_data = ProcessActionInput(
            session_id=session.id,
            action="동쪽으로 이동",
            idempotency_key="normal-turn-key",
        )

        # When
        result = await use_case.execute(session.user_id, input_data)

        # Then: GameActionResponse이며 is_ending=False
        assert isinstance(result.response, GameActionResponse)
        assert result.response.is_ending is False

    @patch("config.settings.settings")
    async def test_final_turn_returns_game_ending_response(self, base_session):
        """Turn 10 (max=10): GameEndingResponse 반환 - 게임 종료."""
        # Given: turn_count=9, advance_turn() 후 10이 됨 → is_final_turn=True
        session = base_session(turn_count=9, max_turns=10)
        repos = self._make_repos(session)
        repos["llm_service"].generate_response.return_value = AsyncMock(
            content="[엔딩 유형]: victory\n[엔딩 내러티브]: 영웅은 마침내 승리했다.",
            usage=AsyncMock(total_tokens=100),
        )
        use_case = self._make_use_case(repos)

        input_data = ProcessActionInput(
            session_id=session.id,
            action="최후의 결전",
            idempotency_key="final-turn-key",
        )

        # When
        result = await use_case.execute(session.user_id, input_data)

        # Then: GameEndingResponse 반환
        assert isinstance(result.response, GameEndingResponse)
        assert result.response.is_ending is True
        assert result.response.total_turns == 10
        assert result.response.session_id == session.id

    @patch("config.settings.settings")
    async def test_game_ending_response_has_character_name(self, base_session):
        """GameEndingResponse에 character_name이 실제 캐릭터 이름으로 채워짐."""
        # Given: turn_count=9 (마지막 턴)
        session = base_session(turn_count=9, max_turns=10)
        repos = self._make_repos(session)
        repos["llm_service"].generate_response.return_value = AsyncMock(
            content="[엔딩 유형]: neutral\n[엔딩 내러티브]: 모험은 끝났다.",
            usage=AsyncMock(total_tokens=80),
        )
        use_case = self._make_use_case(repos)

        input_data = ProcessActionInput(
            session_id=session.id,
            action="마지막 행동",
            idempotency_key="char-name-key",
        )

        # When
        result = await use_case.execute(session.user_id, input_data)

        # Then: character_name이 빈 문자열이 아닌 실제 이름
        assert isinstance(result.response, GameEndingResponse)
        assert result.response.character_name == "테스트 캐릭터"


def test_game_ending_response_is_ending_default_true():
    """GameEndingResponse.is_ending 기본값은 True."""
    response = GameEndingResponse(
        session_id=uuid4(),
        ending_type="victory",
        narrative="게임이 끝났습니다.",
        total_turns=10,
        character_name="용사",
        scenario_name="마왕 토벌",
    )

    assert response.is_ending is True


@pytest.mark.asyncio
class TestScenarioLoading:
    """Test scenario loading in ProcessActionUseCase."""

    @pytest.fixture
    def active_session(self):
        """Create an active game session entity."""
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
            turn_count=0,
            max_turns=10,
            ending_type=None,
            started_at=now,
            last_activity_at=now,
        )
        return session

    @pytest.fixture
    def mock_scenario(self):
        """Create a mock scenario entity."""
        from app.game.domain.entities import ScenarioEntity
        from app.game.domain.value_objects import (
            ScenarioDifficulty,
            ScenarioGenre,
        )

        return ScenarioEntity(
            id=uuid4(),
            name="던전 탐험",
            description="어두운 던전을 탐험하는 모험",
            world_setting="중세 판타지 세계",
            initial_location="던전 입구",
            genre=ScenarioGenre.FANTASY,
            difficulty=ScenarioDifficulty.NORMAL,
            max_turns=30,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

    @pytest.fixture
    def mock_repositories(self, active_session, mock_scenario):
        """Create mocked repositories with scenario."""
        session_repo = AsyncMock()
        session_repo.get_by_id.return_value = active_session

        message_repo = AsyncMock()
        message_repo.get_recent_messages.return_value = []
        message_repo.get_similar_messages.return_value = []

        character_repo = AsyncMock()

        scenario_repo = AsyncMock()
        scenario_repo.get_by_id.return_value = mock_scenario

        llm_service = AsyncMock()
        llm_service.generate_response.return_value = AsyncMock(
            content="You enter the dungeon.",
            usage=AsyncMock(total_tokens=50),
        )

        cache_service = AsyncMock()
        cache_service.get.return_value = None

        embedding_service = AsyncMock()
        embedding_service.generate_embedding.return_value = [0.1] * 768

        return {
            "session_repo": session_repo,
            "message_repo": message_repo,
            "character_repo": character_repo,
            "scenario_repo": scenario_repo,
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
            scenario_repository=mock_repositories["scenario_repo"],
            llm_service=mock_repositories["llm_service"],
            cache_service=mock_repositories["cache_service"],
            embedding_service=mock_repositories["embedding_service"],
        )

    @patch("config.settings.settings")
    async def test_scenario_loaded_in_normal_turn(
        self, use_case, active_session, mock_repositories
    ):
        """시나리오가 _handle_normal_turn에서 로드되는지 확인."""
        input_data = ProcessActionInput(
            session_id=active_session.id,
            action="북쪽으로 이동",
            idempotency_key="scenario-load-key",
        )

        await use_case.execute(active_session.user_id, input_data)

        mock_repositories["scenario_repo"].get_by_id.assert_called_once_with(
            active_session.scenario_id
        )

    @patch("config.settings.settings")
    async def test_scenario_name_passed_to_prompt(
        self, use_case, active_session, mock_repositories
    ):
        """시나리오 이름이 GameMasterPrompt에 전달되는지 확인."""
        input_data = ProcessActionInput(
            session_id=active_session.id,
            action="북쪽으로 이동",
            idempotency_key="scenario-name-key",
        )

        await use_case.execute(active_session.user_id, input_data)

        llm_call_args = mock_repositories[
            "llm_service"
        ].generate_response.call_args
        system_prompt = llm_call_args[1]["system_prompt"]

        assert "던전 탐험" in system_prompt

    @patch("config.settings.settings")
    async def test_scenario_world_setting_passed_to_prompt(
        self, use_case, active_session, mock_repositories
    ):
        """시나리오 world_setting이 GameMasterPrompt에 전달되는지 확인."""
        input_data = ProcessActionInput(
            session_id=active_session.id,
            action="북쪽으로 이동",
            idempotency_key="world-setting-key",
        )

        await use_case.execute(active_session.user_id, input_data)

        llm_call_args = mock_repositories[
            "llm_service"
        ].generate_response.call_args
        system_prompt = llm_call_args[1]["system_prompt"]

        assert "중세 판타지 세계" in system_prompt

    @patch("config.settings.settings")
    async def test_scenario_not_found_raises_error(
        self, use_case, active_session, mock_repositories
    ):
        """시나리오를 찾을 수 없으면 ValueError 발생."""
        mock_repositories["scenario_repo"].get_by_id.return_value = None

        input_data = ProcessActionInput(
            session_id=active_session.id,
            action="북쪽으로 이동",
            idempotency_key="scenario-not-found-key",
        )

        with pytest.raises(ValueError, match="Scenario .* not found"):
            await use_case.execute(active_session.user_id, input_data)
