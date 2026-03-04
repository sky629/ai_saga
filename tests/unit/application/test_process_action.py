"""Unit tests for ProcessActionUseCase.

Tests the business logic of action processing with mocked repositories.
"""

import hashlib
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.common.exception import Conflict
from app.game.application.use_cases.process_action import (
    ProcessActionInput,
    ProcessActionUseCase,
)
from app.game.domain.entities import GameSessionEntity
from app.game.domain.value_objects import SessionStatus
from app.game.presentation.routes.schemas.response import (
    GameActionResponse,
    GameEndingResponse,
    GameMessageResponse,
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
        scenario_mock = MagicMock()
        scenario_mock.name = "테스트 시나리오"
        scenario_mock.difficulty = "normal"
        scenario_repo.get_by_id.return_value = scenario_mock

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
        character_mock = MagicMock()
        character_mock.name = "테스트 캐릭터"
        character_mock.stats.level = 1
        character_repo.get_by_id.return_value = character_mock

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


@pytest.mark.asyncio
class TestProcessActionSecurityAndDeathConsistency:
    @pytest.fixture
    def base_repositories(self):
        session_repo = AsyncMock()
        message_repo = AsyncMock()
        message_repo.get_recent_messages.return_value = []
        message_repo.get_similar_messages.return_value = []
        character_repo = AsyncMock()
        scenario_repo = AsyncMock()
        llm_service = AsyncMock()
        cache_service = AsyncMock()
        cache_service.get.return_value = None
        embedding_service = AsyncMock()
        embedding_service.generate_embedding.return_value = [0.1] * 3
        return {
            "session_repository": session_repo,
            "message_repository": message_repo,
            "character_repository": character_repo,
            "scenario_repository": scenario_repo,
            "llm_service": llm_service,
            "cache_service": cache_service,
            "embedding_service": embedding_service,
        }

    async def test_session_ownership_is_enforced(self, base_repositories):
        from app.common.utils.datetime import get_utc_datetime
        from app.common.utils.id_generator import get_uuid7
        from app.game.domain.entities import GameSessionEntity

        owner_id = get_uuid7()
        request_user_id = get_uuid7()
        session_id = get_uuid7()
        now = get_utc_datetime()

        base_repositories["session_repository"].get_by_id.return_value = (
            GameSessionEntity(
                id=session_id,
                user_id=owner_id,
                character_id=get_uuid7(),
                scenario_id=get_uuid7(),
                current_location="Town",
                game_state={},
                status=SessionStatus.ACTIVE,
                turn_count=1,
                max_turns=10,
                ending_type=None,
                started_at=now,
                last_activity_at=now,
            )
        )

        use_case = ProcessActionUseCase(**base_repositories)
        with pytest.raises(ValueError, match="does not belong to user"):
            await use_case.execute(
                request_user_id,
                ProcessActionInput(
                    session_id=session_id,
                    action="몰래 이동한다",
                    idempotency_key="owner-check-key",
                ),
            )

    async def test_death_check_applies_when_dice_not_applied(
        self, base_repositories
    ):
        from app.common.utils.datetime import get_utc_datetime
        from app.common.utils.id_generator import get_uuid7
        from app.game.domain.entities import (
            CharacterEntity,
            CharacterStats,
            GameSessionEntity,
            ScenarioEntity,
        )

        now = get_utc_datetime()
        user_id = get_uuid7()
        session_id = get_uuid7()
        character_id = get_uuid7()
        scenario_id = get_uuid7()

        session = GameSessionEntity(
            id=session_id,
            user_id=user_id,
            character_id=character_id,
            scenario_id=scenario_id,
            current_location="Dungeon",
            game_state={},
            status=SessionStatus.ACTIVE,
            turn_count=1,
            max_turns=10,
            ending_type=None,
            started_at=now,
            last_activity_at=now,
        )
        scenario = ScenarioEntity(
            id=scenario_id,
            name="테스트 시나리오",
            description="desc",
            world_setting="world",
            initial_location="Dungeon",
            genre="fantasy",
            difficulty="normal",
            max_turns=10,
            is_active=True,
            created_at=now,
        )
        character = CharacterEntity(
            id=character_id,
            user_id=user_id,
            scenario_id=scenario_id,
            name="영웅",
            description="desc",
            stats=CharacterStats(hp=1, max_hp=10, level=1),
            inventory=[],
            is_active=True,
            created_at=now,
        )

        base_repositories["session_repository"].get_by_id.return_value = (
            session
        )
        base_repositories["scenario_repository"].get_by_id.return_value = (
            scenario
        )
        base_repositories["character_repository"].get_by_id.side_effect = [
            character,
            character.update_stats(character.stats.take_damage(1)),
            character.update_stats(character.stats.take_damage(1)),
        ]

        async def save_character(saved_character):
            return saved_character

        base_repositories["character_repository"].save.side_effect = (
            save_character
        )

        llm_response = AsyncMock()
        llm_response.content = (
            '{"narrative": "함정이 터졌다", "options": ["버틴다"], '
            '"dice_applied": false, "state_changes": {"hp_change": -1}}'
        )
        llm_response.usage = AsyncMock(total_tokens=10)
        base_repositories["llm_service"].generate_response.return_value = (
            llm_response
        )

        use_case = ProcessActionUseCase(**base_repositories)
        result = await use_case.execute(
            user_id,
            ProcessActionInput(
                session_id=session_id,
                action="함정 지역으로 이동",
                idempotency_key="death-no-dice-key",
            ),
        )

        assert isinstance(result.response, GameEndingResponse)
        assert result.response.ending_type == "defeat"


@pytest.mark.asyncio
class TestProcessActionIdempotencyPayloadHash:
    @pytest.fixture
    def user_id(self):
        return uuid4()

    @pytest.fixture
    def session_id(self):
        return uuid4()

    @pytest.fixture
    def input_data(self, session_id):
        return ProcessActionInput(
            session_id=session_id,
            action="북쪽으로 이동",
            idempotency_key="idempo-key",
        )

    @pytest.fixture
    def action_response(self, session_id):
        return GameActionResponse(
            message=GameMessageResponse(
                id=uuid4(),
                role="assistant",
                content="결과",
                created_at=datetime.now(timezone.utc),
            ),
            narrative="결과 내러티브",
            options=["다음 행동"],
            turn_count=1,
            max_turns=10,
            session_id=session_id,
        )

    @pytest.fixture
    def use_case(self):
        return ProcessActionUseCase(
            session_repository=AsyncMock(),
            message_repository=AsyncMock(),
            character_repository=AsyncMock(),
            scenario_repository=AsyncMock(),
            llm_service=AsyncMock(),
            cache_service=AsyncMock(),
            embedding_service=AsyncMock(),
        )

    def _payload_hash(self, action: str) -> str:
        return hashlib.sha256(
            json.dumps({"action": action}, sort_keys=True).encode("utf-8")
        ).hexdigest()

    async def test_execute_raises_conflict_when_cached_payload_hash_mismatch(
        self, use_case, input_data, action_response, user_id
    ):
        use_case._cache.get.return_value = json.dumps(
            {
                "type": "action",
                "payload_hash": "different-hash",
                "data": action_response.model_dump(mode="json"),
            }
        )

        with pytest.raises(Conflict):
            await use_case.execute(user_id, input_data)

    async def test_execute_returns_cached_when_payload_hash_matches(
        self, use_case, input_data, action_response, user_id
    ):
        use_case._cache.get.return_value = json.dumps(
            {
                "type": "action",
                "payload_hash": self._payload_hash(input_data.action),
                "data": action_response.model_dump(mode="json"),
            }
        )

        result = await use_case.execute(user_id, input_data)

        assert result.is_cached is True
        assert isinstance(result.response, GameActionResponse)
        assert result.response.narrative == "결과 내러티브"
        use_case._session_repo.get_by_id.assert_not_called()

    async def test_execute_caches_response_with_payload_hash(
        self, use_case, input_data, action_response, user_id
    ):
        now = datetime.now(timezone.utc)
        session = GameSessionEntity(
            id=input_data.session_id,
            user_id=user_id,
            character_id=uuid4(),
            scenario_id=uuid4(),
            current_location="Forest",
            game_state={},
            status=SessionStatus.ACTIVE,
            turn_count=0,
            max_turns=10,
            ending_type=None,
            started_at=now,
            last_activity_at=now,
        )
        use_case._cache.get.return_value = None
        use_case._session_repo.get_by_id.return_value = session
        use_case._embedding.generate_embedding.return_value = [0.1, 0.2, 0.3]
        use_case._message_repo.get_recent_messages.return_value = []
        use_case._message_repo.get_similar_messages.return_value = []
        use_case._handle_normal_turn = AsyncMock(
            return_value=(session.advance_turn(), action_response)
        )

        await use_case.execute(user_id, input_data)

        use_case._cache.set.assert_called_once()
        cache_payload = json.loads(use_case._cache.set.call_args.args[1])
        assert cache_payload["payload_hash"] == self._payload_hash(
            input_data.action
        )


@pytest.mark.asyncio
class TestProcessActionCommitOrdering:
    async def test_execute_commits_before_cache_set(self):
        user_id = uuid4()
        session_id = uuid4()
        now = datetime.now(timezone.utc)
        session = GameSessionEntity(
            id=session_id,
            user_id=user_id,
            character_id=uuid4(),
            scenario_id=uuid4(),
            current_location="Forest",
            game_state={},
            status=SessionStatus.ACTIVE,
            turn_count=0,
            max_turns=10,
            ending_type=None,
            started_at=now,
            last_activity_at=now,
        )

        session_repo = AsyncMock()
        session_repo.get_by_id.return_value = session
        session_repo.save.return_value = session

        message_repo = AsyncMock()
        message_repo.get_recent_messages.return_value = []
        message_repo.get_similar_messages.return_value = []

        character_repo = AsyncMock()
        character = MagicMock()
        character.name = "Hero"
        character.stats.level = 1
        character_repo.get_by_id.return_value = character

        scenario_repo = AsyncMock()
        scenario = MagicMock()
        scenario.name = "Scenario"
        scenario.difficulty = "normal"
        scenario_repo.get_by_id.return_value = scenario

        llm_service = AsyncMock()
        llm_service.generate_response.return_value = AsyncMock(
            content="계속 진행합니다.",
            usage=AsyncMock(total_tokens=10),
        )

        cache_service = AsyncMock()
        cache_service.get.return_value = None

        call_order: list[str] = []

        async def commit_side_effect():
            call_order.append("commit")

        async def cache_set_side_effect(*args, **kwargs):
            call_order.append("cache_set")

        session_repo.commit.side_effect = commit_side_effect
        cache_service.set.side_effect = cache_set_side_effect

        embedding_service = AsyncMock()
        embedding_service.generate_embedding.return_value = [0.1] * 768

        use_case = ProcessActionUseCase(
            session_repository=session_repo,
            message_repository=message_repo,
            character_repository=character_repo,
            scenario_repository=scenario_repo,
            llm_service=llm_service,
            cache_service=cache_service,
            embedding_service=embedding_service,
        )

        await use_case.execute(
            user_id,
            ProcessActionInput(
                session_id=session_id,
                action="주변을 탐색한다",
                idempotency_key="commit-order-key",
            ),
        )

        assert call_order == ["commit", "cache_set"]

    async def test_execute_does_not_cache_when_commit_fails(self):
        user_id = uuid4()
        session_id = uuid4()
        now = datetime.now(timezone.utc)
        session = GameSessionEntity(
            id=session_id,
            user_id=user_id,
            character_id=uuid4(),
            scenario_id=uuid4(),
            current_location="Forest",
            game_state={},
            status=SessionStatus.ACTIVE,
            turn_count=0,
            max_turns=10,
            ending_type=None,
            started_at=now,
            last_activity_at=now,
        )

        session_repo = AsyncMock()
        session_repo.get_by_id.return_value = session
        session_repo.save.return_value = session
        session_repo.commit.side_effect = RuntimeError("commit failed")

        message_repo = AsyncMock()
        message_repo.get_recent_messages.return_value = []
        message_repo.get_similar_messages.return_value = []

        character_repo = AsyncMock()
        character = MagicMock()
        character.name = "Hero"
        character.stats.level = 1
        character_repo.get_by_id.return_value = character

        scenario_repo = AsyncMock()
        scenario = MagicMock()
        scenario.name = "Scenario"
        scenario.difficulty = "normal"
        scenario_repo.get_by_id.return_value = scenario

        llm_service = AsyncMock()
        llm_service.generate_response.return_value = AsyncMock(
            content="계속 진행합니다.",
            usage=AsyncMock(total_tokens=10),
        )

        cache_service = AsyncMock()
        cache_service.get.return_value = None

        embedding_service = AsyncMock()
        embedding_service.generate_embedding.return_value = [0.1] * 768

        use_case = ProcessActionUseCase(
            session_repository=session_repo,
            message_repository=message_repo,
            character_repository=character_repo,
            scenario_repository=scenario_repo,
            llm_service=llm_service,
            cache_service=cache_service,
            embedding_service=embedding_service,
        )

        with pytest.raises(RuntimeError, match="commit failed"):
            await use_case.execute(
                user_id,
                ProcessActionInput(
                    session_id=session_id,
                    action="주변을 탐색한다",
                    idempotency_key="commit-fail-key",
                ),
            )

        cache_service.set.assert_not_called()
