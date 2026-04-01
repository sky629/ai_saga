"""GenerateIllustrationUseCase 단위 테스트."""

from typing import Optional
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from app.common.utils.datetime import get_utc_datetime
from app.common.utils.id_generator import get_uuid7
from app.game.application.ports import (
    CacheServiceInterface,
    GameMessageRepositoryInterface,
    GameSessionRepositoryInterface,
    ImageGenerationServiceInterface,
    ScenarioRepositoryInterface,
)
from app.game.application.use_cases.generate_illustration import (
    GenerateIllustrationInput,
    GenerateIllustrationUseCase,
)
from app.game.domain.entities import (
    CharacterEntity,
    GameMessageEntity,
    GameSessionEntity,
    ScenarioEntity,
)
from app.game.domain.entities.character import CharacterProfile
from app.game.domain.value_objects import GameType, MessageRole, SessionStatus
from config.settings import settings


def _make_session(session_id: UUID, user_id: UUID) -> GameSessionEntity:
    return GameSessionEntity(
        id=session_id,
        user_id=user_id,
        character_id=get_uuid7(),
        scenario_id=get_uuid7(),
        current_location="숲 속",
        game_state={},
        status=SessionStatus.ACTIVE,
        turn_count=3,
        max_turns=30,
        ending_type=None,
        started_at=get_utc_datetime(),
        ended_at=None,
        last_activity_at=get_utc_datetime(),
    )


def _make_ai_message(
    message_id: UUID, session_id: UUID, image_url: Optional[str] = None
) -> GameMessageEntity:
    return GameMessageEntity(
        id=message_id,
        session_id=session_id,
        role=MessageRole.ASSISTANT,
        content="고블린이 당신을 향해 달려옵니다.",
        parsed_response={
            "narrative": "고블린이 당신을 향해 달려옵니다.",
            "state_changes": {
                "location": "서울역 지하 통로",
                "npcs_met": ["하윤"],
                "discoveries": ["깨진 비상 방송 장치"],
            },
        },
        token_count=None,
        image_url=image_url,
        created_at=get_utc_datetime(),
    )


class TestGenerateIllustrationUseCase:
    """GenerateIllustrationUseCase 단위 테스트."""

    @pytest.fixture
    def mock_session_repo(self):
        return AsyncMock(spec=GameSessionRepositoryInterface)

    @pytest.fixture
    def mock_message_repo(self):
        return AsyncMock(spec=GameMessageRepositoryInterface)

    @pytest.fixture
    def mock_character_repo(self):
        return AsyncMock()

    @pytest.fixture
    def mock_scenario_repo(self):
        return AsyncMock(spec=ScenarioRepositoryInterface)

    @pytest.fixture
    def mock_cache_service(self):
        return AsyncMock(spec=CacheServiceInterface)

    @pytest.fixture
    def mock_image_service(self):
        return AsyncMock(spec=ImageGenerationServiceInterface)

    @pytest.fixture
    def use_case(
        self,
        mock_session_repo,
        mock_message_repo,
        mock_character_repo,
        mock_scenario_repo,
        mock_cache_service,
        mock_image_service,
    ):
        return GenerateIllustrationUseCase(
            session_repository=mock_session_repo,
            message_repository=mock_message_repo,
            character_repository=mock_character_repo,
            scenario_repository=mock_scenario_repo,
            cache_service=mock_cache_service,
            image_service=mock_image_service,
        )

    @pytest.mark.asyncio
    async def test_generate_illustration_success(
        self,
        use_case,
        mock_session_repo,
        mock_message_repo,
        mock_character_repo,
        mock_scenario_repo,
        mock_cache_service,
        mock_image_service,
    ):
        """정상 케이스: 메시지 조회 → 이미지 생성 → 메시지 저장 → URL 반환."""
        user_id = get_uuid7()
        session_id = get_uuid7()
        message_id = get_uuid7()
        expected_url = "https://r2.example.com/images/test.png"

        session = _make_session(session_id, user_id)
        message = _make_ai_message(message_id, session_id)
        character = CharacterEntity(
            id=session.character_id,
            user_id=user_id,
            scenario_id=get_uuid7(),
            name="실비아",
            profile=CharacterProfile(
                age=27,
                gender="여성",
                appearance="검은 단발과 오래된 흉터",
                goal="실종된 형을 찾는 것",
            ),
            stats={},
            inventory=[],
            is_active=True,
            created_at=get_utc_datetime(),
        )
        scenario = ScenarioEntity(
            id=session.scenario_id,
            name="좀비 아포칼립스",
            description="탈출 시나리오",
            world_setting=(
                "폐허가 된 서울에서 생존자와 좀비가 뒤엉킨다. "
                "감염체는 소리와 움직임, 피 냄새에 민감하다."
            ),
            initial_location="숲 속",
            game_type=GameType.TRPG,
            genre="survival",
            difficulty="normal",
            max_turns=30,
            is_active=True,
            created_at=get_utc_datetime(),
            updated_at=get_utc_datetime(),
        )

        mock_session_repo.get_by_id.return_value = session
        mock_message_repo.get_by_id.return_value = message
        mock_character_repo.get_by_id.return_value = character
        mock_scenario_repo.get_by_id.return_value = scenario
        mock_cache_service.get.return_value = None
        mock_image_service.generate_image.return_value = expected_url
        mock_message_repo.update_image_url.return_value = message.model_copy(
            update={"image_url": expected_url}
        )

        input_data = GenerateIllustrationInput(
            session_id=session_id,
            message_id=message_id,
        )
        result = await use_case.execute(user_id, input_data)

        assert result.image_url == expected_url
        assert result.message_id == message_id
        mock_image_service.generate_image.assert_called_once()
        called_prompt = mock_image_service.generate_image.call_args.kwargs[
            "prompt"
        ]
        assert "Depict this exact story moment:" in called_prompt
        assert "Single-panel illustration only." in called_prompt
        assert "No readable text" in called_prompt
        assert "This must look like a clean illustration" in called_prompt
        assert "Set the scene at 서울역 지하 통로." in called_prompt
        assert "The main focus is 실비아." in called_prompt
        assert "These scene facts must stay true:" in called_prompt
        assert "zombie apocalypse" in called_prompt.lower()
        mock_cache_service.set.assert_called_once_with(
            f"game:illustration:result:{message_id}",
            expected_url,
            ttl_seconds=86400,
        )
        mock_message_repo.update_image_url.assert_called_once_with(
            message_id, expected_url
        )

    @pytest.mark.asyncio
    async def test_uses_cached_result_without_generating_again(
        self,
        use_case,
        mock_session_repo,
        mock_message_repo,
        mock_character_repo,
        mock_scenario_repo,
        mock_cache_service,
        mock_image_service,
    ):
        """캐시된 이미지 URL이 있으면 LLM 재호출 없이 재사용한다."""
        user_id = get_uuid7()
        session_id = get_uuid7()
        message_id = get_uuid7()
        cached_url = "https://r2.example.com/images/cached.png"

        session = _make_session(session_id, user_id)
        message = _make_ai_message(message_id, session_id)

        mock_session_repo.get_by_id.return_value = session
        mock_message_repo.get_by_id.return_value = message
        mock_cache_service.get.return_value = cached_url

        result = await use_case.execute(
            user_id,
            GenerateIllustrationInput(
                session_id=session_id,
                message_id=message_id,
            ),
        )

        assert result.image_url == cached_url
        mock_image_service.generate_image.assert_not_called()
        mock_character_repo.get_by_id.assert_not_called()
        mock_scenario_repo.get_by_id.assert_not_called()
        mock_message_repo.update_image_url.assert_called_once_with(
            message_id, cached_url
        )

    @pytest.mark.asyncio
    async def test_raises_if_session_not_found(
        self,
        use_case,
        mock_session_repo,
        mock_message_repo,
    ):
        """세션이 없으면 NotFound 예외."""
        from app.common.exception import NotFound

        mock_session_repo.get_by_id.return_value = None

        input_data = GenerateIllustrationInput(
            session_id=get_uuid7(),
            message_id=get_uuid7(),
        )
        with pytest.raises(NotFound):
            await use_case.execute(get_uuid7(), input_data)

    @pytest.mark.asyncio
    async def test_raises_if_session_belongs_to_other_user(
        self,
        use_case,
        mock_session_repo,
    ):
        """다른 유저의 세션이면 Forbidden 예외."""
        from app.common.exception import Forbidden

        session_id = get_uuid7()
        session = _make_session(
            session_id, user_id=get_uuid7()
        )  # 다른 user_id
        mock_session_repo.get_by_id.return_value = session

        input_data = GenerateIllustrationInput(
            session_id=session_id,
            message_id=get_uuid7(),
        )
        with pytest.raises(Forbidden):
            await use_case.execute(
                get_uuid7(), input_data
            )  # 다른 user_id로 요청

    @pytest.mark.asyncio
    async def test_raises_if_message_not_found(
        self,
        use_case,
        mock_session_repo,
        mock_message_repo,
    ):
        """메시지가 없으면 NotFound 예외."""
        from app.common.exception import NotFound

        user_id = get_uuid7()
        session_id = get_uuid7()
        session = _make_session(session_id, user_id)

        mock_session_repo.get_by_id.return_value = session
        mock_message_repo.get_by_id.return_value = None

        input_data = GenerateIllustrationInput(
            session_id=session_id,
            message_id=get_uuid7(),
        )
        with pytest.raises(NotFound):
            await use_case.execute(user_id, input_data)

    @pytest.mark.asyncio
    async def test_raises_if_message_not_ai_response(
        self,
        use_case,
        mock_session_repo,
        mock_message_repo,
    ):
        """유저 메시지에는 일러스트 생성 불가 → BadRequest 예외."""
        from app.common.exception import BadRequest

        user_id = get_uuid7()
        session_id = get_uuid7()
        message_id = get_uuid7()

        session = _make_session(session_id, user_id)
        user_message = GameMessageEntity(
            id=message_id,
            session_id=session_id,
            role=MessageRole.USER,  # USER 메시지
            content="앞으로 나아갑니다.",
            parsed_response=None,
            token_count=None,
            image_url=None,
            created_at=get_utc_datetime(),
        )

        mock_session_repo.get_by_id.return_value = session
        mock_message_repo.get_by_id.return_value = user_message

        input_data = GenerateIllustrationInput(
            session_id=session_id,
            message_id=message_id,
        )
        with pytest.raises(BadRequest):
            await use_case.execute(user_id, input_data)

    @pytest.mark.asyncio
    async def test_raises_if_message_session_mismatch(
        self,
        use_case,
        mock_session_repo,
        mock_message_repo,
    ):
        """요청 세션과 메시지 소속 세션이 다르면 BadRequest."""
        from app.common.exception import BadRequest

        user_id = get_uuid7()
        requested_session_id = get_uuid7()
        other_session_id = get_uuid7()
        message_id = get_uuid7()

        mock_session_repo.get_by_id.return_value = _make_session(
            requested_session_id, user_id
        )
        mock_message_repo.get_by_id.return_value = _make_ai_message(
            message_id, other_session_id
        )

        with pytest.raises(BadRequest):
            await use_case.execute(
                user_id,
                GenerateIllustrationInput(
                    session_id=requested_session_id,
                    message_id=message_id,
                ),
            )

    @pytest.mark.asyncio
    async def test_returns_existing_url_if_already_generated(
        self,
        use_case,
        mock_session_repo,
        mock_message_repo,
        mock_image_service,
    ):
        """이미 image_url이 있으면 이미지 재생성 없이 기존 URL 반환."""
        user_id = get_uuid7()
        session_id = get_uuid7()
        message_id = get_uuid7()
        existing_url = "https://r2.example.com/images/existing.png"

        session = _make_session(session_id, user_id)
        message = _make_ai_message(
            message_id, session_id, image_url=existing_url
        )

        mock_session_repo.get_by_id.return_value = session
        mock_message_repo.get_by_id.return_value = message

        input_data = GenerateIllustrationInput(
            session_id=session_id,
            message_id=message_id,
        )
        result = await use_case.execute(user_id, input_data)

        assert result.image_url == existing_url
        mock_image_service.generate_image.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_server_error_if_image_generation_fails(
        self,
        use_case,
        mock_session_repo,
        mock_message_repo,
        mock_character_repo,
        mock_scenario_repo,
        mock_cache_service,
        mock_image_service,
    ):
        """이미지 생성 실패 시 ServerError 예외."""
        from app.common.exception import ServerError

        user_id = get_uuid7()
        session_id = get_uuid7()
        message_id = get_uuid7()

        session = _make_session(session_id, user_id)
        message = _make_ai_message(message_id, session_id)
        character = CharacterEntity(
            id=session.character_id,
            user_id=user_id,
            scenario_id=get_uuid7(),
            name="실비아",
            profile=CharacterProfile(
                age=27,
                gender="여성",
                appearance="검은 단발과 오래된 흉터",
                goal="실종된 형을 찾는 것",
            ),
            stats={},
            inventory=[],
            is_active=True,
            created_at=get_utc_datetime(),
        )
        scenario = ScenarioEntity(
            id=session.scenario_id,
            name="감옥 탈출",
            description="탈출 시나리오",
            world_setting="지하 감옥과 오래된 왕국",
            initial_location="숲 속",
            game_type=GameType.TRPG,
            genre="fantasy",
            difficulty="normal",
            max_turns=30,
            is_active=True,
            created_at=get_utc_datetime(),
            updated_at=get_utc_datetime(),
        )

        mock_session_repo.get_by_id.return_value = session
        mock_message_repo.get_by_id.return_value = message
        mock_character_repo.get_by_id.return_value = character
        mock_scenario_repo.get_by_id.return_value = scenario
        mock_cache_service.get.return_value = None
        mock_image_service.generate_image.return_value = (
            None  # 실패 시 None 반환
        )

        input_data = GenerateIllustrationInput(
            session_id=session_id,
            message_id=message_id,
        )
        with pytest.raises(ServerError):
            await use_case.execute(user_id, input_data)

    @pytest.mark.asyncio
    async def test_uses_dummy_image_when_feature_disabled(
        self,
        use_case,
        mock_session_repo,
        mock_message_repo,
        mock_character_repo,
        mock_scenario_repo,
        mock_cache_service,
        mock_image_service,
        monkeypatch,
    ):
        """비활성화 상태에서는 더미 이미지 경로로 처리한다."""
        user_id = get_uuid7()
        session_id = get_uuid7()
        message_id = get_uuid7()
        expected_url = "https://example.com/dummy-image.png"

        session = _make_session(session_id, user_id)
        message = _make_ai_message(message_id, session_id)
        character = CharacterEntity(
            id=session.character_id,
            user_id=user_id,
            scenario_id=get_uuid7(),
            name="실비아",
            profile=CharacterProfile(
                age=27,
                gender="여성",
                appearance="검은 단발과 오래된 흉터",
                goal="실종된 형을 찾는 것",
            ),
            stats={},
            inventory=[],
            is_active=True,
            created_at=get_utc_datetime(),
        )
        scenario = ScenarioEntity(
            id=session.scenario_id,
            name="감옥 탈출",
            description="탈출 시나리오",
            world_setting="지하 감옥과 오래된 왕국",
            initial_location="숲 속",
            game_type=GameType.TRPG,
            genre="fantasy",
            difficulty="normal",
            max_turns=30,
            is_active=True,
            created_at=get_utc_datetime(),
            updated_at=get_utc_datetime(),
        )

        mock_session_repo.get_by_id.return_value = session
        mock_message_repo.get_by_id.return_value = message
        mock_character_repo.get_by_id.return_value = character
        mock_scenario_repo.get_by_id.return_value = scenario
        mock_cache_service.get.return_value = None
        mock_image_service.generate_image.return_value = expected_url
        monkeypatch.setattr(settings, "image_generation_enabled", False)

        result = await use_case.execute(
            user_id,
            GenerateIllustrationInput(
                session_id=session_id,
                message_id=message_id,
            ),
        )

        assert result.image_url == expected_url
        mock_image_service.generate_image.assert_called_once()
        mock_message_repo.update_image_url.assert_called_once_with(
            message_id, expected_url
        )

    @pytest.mark.asyncio
    async def test_cleans_up_uploaded_image_when_db_update_fails(
        self,
        use_case,
        mock_session_repo,
        mock_message_repo,
        mock_character_repo,
        mock_scenario_repo,
        mock_cache_service,
        mock_image_service,
    ):
        """DB 반영 실패 시 업로드 이미지와 캐시를 정리한다."""
        user_id = get_uuid7()
        session_id = get_uuid7()
        message_id = get_uuid7()
        generated_url = "https://r2.example.com/images/test.png"

        session = _make_session(session_id, user_id)
        message = _make_ai_message(message_id, session_id)
        character = CharacterEntity(
            id=session.character_id,
            user_id=user_id,
            scenario_id=get_uuid7(),
            name="실비아",
            profile=CharacterProfile(
                age=27,
                gender="여성",
                appearance="검은 단발과 오래된 흉터",
                goal="실종된 형을 찾는 것",
            ),
            stats={},
            inventory=[],
            is_active=True,
            created_at=get_utc_datetime(),
        )
        scenario = ScenarioEntity(
            id=session.scenario_id,
            name="감옥 탈출",
            description="탈출 시나리오",
            world_setting="지하 감옥과 오래된 왕국",
            initial_location="숲 속",
            game_type=GameType.TRPG,
            genre="fantasy",
            difficulty="normal",
            max_turns=30,
            is_active=True,
            created_at=get_utc_datetime(),
            updated_at=get_utc_datetime(),
        )

        mock_session_repo.get_by_id.return_value = session
        mock_message_repo.get_by_id.return_value = message
        mock_character_repo.get_by_id.return_value = character
        mock_scenario_repo.get_by_id.return_value = scenario
        mock_cache_service.get.return_value = None
        mock_image_service.generate_image.return_value = generated_url
        mock_message_repo.update_image_url.side_effect = Exception("db failed")

        with pytest.raises(Exception, match="db failed"):
            await use_case.execute(
                user_id,
                GenerateIllustrationInput(
                    session_id=session_id,
                    message_id=message_id,
                ),
            )

        mock_image_service.delete_image.assert_called_once_with(generated_url)
        mock_cache_service.delete.assert_called_once_with(
            f"game:illustration:result:{message_id}"
        )
