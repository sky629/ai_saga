from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from app.common.utils.datetime import get_utc_datetime
from app.common.utils.id_generator import get_uuid7
from app.game.application.ports import (
    UserProgressionInterface,
    UserProgressionResult,
)
from app.game.application.use_cases.process_action import ProcessActionUseCase
from app.game.domain.entities import (
    CharacterEntity,
    GameMessageEntity,
    GameSessionEntity,
)
from app.game.domain.value_objects import (
    EndingType,
    MessageRole,
    SessionStatus,
)
from app.game.domain.value_objects.scenario_difficulty import (
    ScenarioDifficulty,
)
from app.game.presentation.routes.schemas.response import (
    GameActionResponse,
    GameEndingResponse,
)


@pytest.fixture
def user_id() -> UUID:
    return get_uuid7()


@pytest.fixture
def session_id() -> UUID:
    return get_uuid7()


@pytest.fixture
def mock_session(session_id: UUID, user_id: UUID) -> GameSessionEntity:
    now = get_utc_datetime()
    return GameSessionEntity(
        id=session_id,
        user_id=user_id,
        character_id=get_uuid7(),
        scenario_id=get_uuid7(),
        status=SessionStatus.ACTIVE,
        turn_count=5,
        max_turns=10,
        current_location="던전",
        game_state={},
        started_at=now,
        last_activity_at=now,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def mock_scenario():
    scenario = MagicMock()
    scenario.difficulty = ScenarioDifficulty.NORMAL
    scenario.name = "테스트 시나리오"
    scenario.world_setting = "판타지 세계"
    return scenario


@pytest.fixture
def mock_progression_result() -> UserProgressionResult:
    return UserProgressionResult(
        game_level=2,
        game_experience=350,
        game_current_experience=50,
        leveled_up=True,
        levels_gained=1,
    )


@pytest.fixture
def mock_user_progression(
    mock_progression_result: UserProgressionResult,
) -> AsyncMock:
    mock = AsyncMock(spec=UserProgressionInterface)
    mock.award_game_experience.return_value = mock_progression_result
    return mock


@pytest.fixture
def use_case(mock_user_progression: AsyncMock) -> ProcessActionUseCase:
    return ProcessActionUseCase(
        session_repository=AsyncMock(),
        message_repository=AsyncMock(),
        character_repository=AsyncMock(),
        scenario_repository=AsyncMock(),
        llm_service=AsyncMock(),
        cache_service=AsyncMock(),
        embedding_service=AsyncMock(),
        user_progression=mock_user_progression,
    )


@pytest.fixture
def use_case_no_progression() -> ProcessActionUseCase:
    return ProcessActionUseCase(
        session_repository=AsyncMock(),
        message_repository=AsyncMock(),
        character_repository=AsyncMock(),
        scenario_repository=AsyncMock(),
        llm_service=AsyncMock(),
        cache_service=AsyncMock(),
        embedding_service=AsyncMock(),
        user_progression=None,
    )


@pytest.fixture
def recent_messages() -> list:
    return []


@pytest.mark.asyncio
async def test_handle_ending_awards_xp_victory(
    use_case: ProcessActionUseCase,
    mock_session: GameSessionEntity,
    mock_scenario: MagicMock,
    mock_user_progression: AsyncMock,
    user_id: UUID,
    recent_messages: list,
):
    use_case._scenario_repo.get_by_id.return_value = mock_scenario
    mock_character = MagicMock()
    mock_character.name = "영웅"
    use_case._character_repo.get_by_id.return_value = mock_character
    use_case._message_repo.create.return_value = None
    mock_llm_response = MagicMock()
    mock_llm_response.content = (
        "[엔딩 유형]: victory\n[엔딩 내러티브]: 당신은 승리했습니다!"
    )
    mock_llm_response.usage = None
    use_case._llm.generate_response.return_value = mock_llm_response

    _, response = await use_case._handle_ending(
        mock_session, recent_messages, user_id
    )

    assert isinstance(response, GameEndingResponse)
    assert response.xp_gained > 0
    assert response.new_game_level == 2
    assert response.leveled_up is True
    assert response.levels_gained == 1
    mock_user_progression.award_game_experience.assert_called_once()


@pytest.mark.asyncio
async def test_handle_ending_awards_xp_defeat(
    use_case: ProcessActionUseCase,
    mock_session: GameSessionEntity,
    mock_scenario: MagicMock,
    mock_user_progression: AsyncMock,
    user_id: UUID,
    recent_messages: list,
):
    use_case._scenario_repo.get_by_id.return_value = mock_scenario
    mock_character = MagicMock()
    mock_character.name = "영웅"
    use_case._character_repo.get_by_id.return_value = mock_character
    use_case._message_repo.create.return_value = None
    mock_progression_result_defeat = UserProgressionResult(
        game_level=1,
        game_experience=75,
        game_current_experience=75,
        leveled_up=False,
        levels_gained=0,
    )
    mock_user_progression.award_game_experience.return_value = (
        mock_progression_result_defeat
    )
    mock_llm_response = MagicMock()
    mock_llm_response.content = (
        "[엔딩 유형]: defeat\n[엔딩 내러티브]: 패배했습니다."
    )
    mock_llm_response.usage = None
    use_case._llm.generate_response.return_value = mock_llm_response

    _, response = await use_case._handle_ending(
        mock_session, recent_messages, user_id
    )

    assert isinstance(response, GameEndingResponse)
    assert response.xp_gained > 0
    assert response.xp_gained == 75
    mock_user_progression.award_game_experience.assert_called_once_with(
        user_id, 75
    )


@pytest.mark.asyncio
async def test_handle_ending_xp_failure_doesnt_break(
    use_case: ProcessActionUseCase,
    mock_session: GameSessionEntity,
    mock_scenario: MagicMock,
    mock_user_progression: AsyncMock,
    user_id: UUID,
    recent_messages: list,
):
    use_case._scenario_repo.get_by_id.return_value = mock_scenario
    mock_character = MagicMock()
    mock_character.name = "영웅"
    use_case._character_repo.get_by_id.return_value = mock_character
    use_case._message_repo.create.return_value = None
    mock_user_progression.award_game_experience.side_effect = Exception(
        "DB 연결 실패"
    )
    mock_llm_response = MagicMock()
    mock_llm_response.content = "[엔딩 유형]: victory\n[엔딩 내러티브]: 승리!"
    mock_llm_response.usage = None
    use_case._llm.generate_response.return_value = mock_llm_response

    _, response = await use_case._handle_ending(
        mock_session, recent_messages, user_id
    )

    assert isinstance(response, GameEndingResponse)
    assert response.xp_gained == 0
    assert response.new_game_level == 1
    assert response.leveled_up is False


@pytest.mark.asyncio
async def test_handle_ending_without_user_progression(
    use_case_no_progression: ProcessActionUseCase,
    mock_session: GameSessionEntity,
    user_id: UUID,
    recent_messages: list,
):
    use_case_no_progression._scenario_repo.get_by_id.return_value = None
    mock_character = MagicMock()
    mock_character.name = "영웅"
    use_case_no_progression._character_repo.get_by_id.return_value = (
        mock_character
    )
    use_case_no_progression._message_repo.create.return_value = None
    mock_llm_response = MagicMock()
    mock_llm_response.content = (
        "[엔딩 유형]: neutral\n[엔딩 내러티브]: 중립 결말."
    )
    mock_llm_response.usage = None
    use_case_no_progression._llm.generate_response.return_value = (
        mock_llm_response
    )

    _, response = await use_case_no_progression._handle_ending(
        mock_session, recent_messages, user_id
    )

    assert isinstance(response, GameEndingResponse)
    assert response.xp_gained == 0
    assert response.leveled_up is False


@pytest.mark.asyncio
async def test_death_ending_awards_defeat_xp(
    use_case: ProcessActionUseCase,
    mock_session: GameSessionEntity,
    mock_scenario: MagicMock,
    mock_user_progression: AsyncMock,
    user_id: UUID,
    recent_messages: list,
):
    use_case._scenario_repo.get_by_id.return_value = mock_scenario
    mock_progression_result_defeat = UserProgressionResult(
        game_level=1,
        game_experience=75,
        game_current_experience=75,
        leveled_up=False,
        levels_gained=0,
    )
    mock_user_progression.award_game_experience.return_value = (
        mock_progression_result_defeat
    )
    use_case._message_repo.create.return_value = None
    mock_character = MagicMock()
    mock_character.name = "용사"

    response = await use_case._handle_death_ending(
        mock_session,
        mock_character,
        "용사가 쓰러졌다.",
        recent_messages,
        user_id,
    )

    assert isinstance(response, GameActionResponse)
    assert response.is_ending is True
    assert response.xp_gained == 75
    mock_user_progression.award_game_experience.assert_called_once_with(
        user_id, 75
    )


@pytest.mark.asyncio
async def test_death_ending_xp_failure_doesnt_break(
    use_case: ProcessActionUseCase,
    mock_session: GameSessionEntity,
    mock_scenario: MagicMock,
    mock_user_progression: AsyncMock,
    user_id: UUID,
    recent_messages: list,
):
    use_case._scenario_repo.get_by_id.return_value = mock_scenario
    mock_user_progression.award_game_experience.side_effect = Exception(
        "네트워크 오류"
    )
    use_case._message_repo.create.return_value = None
    mock_character = MagicMock()
    mock_character.name = "용사"

    response = await use_case._handle_death_ending(
        mock_session,
        mock_character,
        "용사가 쓰러졌다.",
        recent_messages,
        user_id,
    )

    assert isinstance(response, GameActionResponse)
    assert response.is_ending is True
    assert response.xp_gained is None
