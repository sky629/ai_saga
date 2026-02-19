"""ProcessActionUseCase 경험치 시스템 단위 테스트."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.common.utils.id_generator import get_uuid7
from app.game.application.use_cases.process_action import (
    ProcessActionInput,
    ProcessActionUseCase,
)
from app.game.domain.entities.character import CharacterEntity, CharacterStats
from app.game.domain.entities.game_session import (
    GameSessionEntity,
    SessionStatus,
)


@pytest.fixture
def mock_repositories():
    """Mock repositories for testing."""
    return {
        "session_repository": AsyncMock(),
        "character_repository": AsyncMock(),
        "message_repository": AsyncMock(),
        "cache_service": AsyncMock(),
        "embedding_service": AsyncMock(),
    }


@pytest.fixture
def mock_llm_service():
    """Mock LLM service."""
    return AsyncMock()


@pytest.fixture
def test_character():
    """Create test character (레벨업 없음 시나리오용: current_experience=50)."""
    return CharacterEntity(
        id=get_uuid7(),
        user_id=get_uuid7(),
        scenario_id=get_uuid7(),
        name="테스트 캐릭터",
        description="테스트용",
        stats=CharacterStats(
            hp=100,
            max_hp=100,
            level=1,
            experience=50,
            current_experience=50,
        ),
        inventory=[],
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def test_character_near_levelup():
    """Create test character (레벨업 시나리오용: current_experience=90)."""
    return CharacterEntity(
        id=get_uuid7(),
        user_id=get_uuid7(),
        scenario_id=get_uuid7(),
        name="테스트 캐릭터",
        description="테스트용",
        stats=CharacterStats(
            hp=100,
            max_hp=100,
            level=1,
            experience=90,
            current_experience=90,
        ),
        inventory=[],
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def test_session(test_character):
    """Create test session."""
    return GameSessionEntity(
        id=get_uuid7(),
        user_id=test_character.user_id,
        character_id=test_character.id,
        scenario_id=test_character.scenario_id,
        current_location="테스트 장소",
        game_state={},
        status=SessionStatus.ACTIVE,
        turn_count=0,
        max_turns=30,
        ending_type=None,
        started_at=datetime.now(timezone.utc),
        ended_at=None,
        last_activity_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_process_action_with_experience_gain(
    mock_repositories,
    mock_llm_service,
    test_character,
    test_session,
):
    """경험치 획득 (레벨업 없음) 테스트."""
    # Given
    use_case = ProcessActionUseCase(
        session_repository=mock_repositories["session_repository"],
        character_repository=mock_repositories["character_repository"],
        message_repository=mock_repositories["message_repository"],
        llm_service=mock_llm_service,
        cache_service=mock_repositories["cache_service"],
        embedding_service=mock_repositories["embedding_service"],
    )

    # Mock repository responses
    mock_repositories["session_repository"].get_by_id.return_value = (
        test_session
    )
    mock_repositories["character_repository"].get_by_id.return_value = (
        test_character
    )
    mock_repositories["cache_service"].get.return_value = (
        None  # No cached result
    )

    # Mock LLM response with experience gain
    llm_response_content = """```json
{
    "narrative": "고블린을 처치했습니다!",
    "options": ["계속 진행", "휴식"],
    "state_changes": {
        "experience_gained": 30
    }
}
```"""
    mock_llm_response = MagicMock()
    mock_llm_response.content = llm_response_content
    mock_llm_service.generate_context_string.return_value = "context"
    mock_llm_service.generate_response.return_value = mock_llm_response

    # When
    input_data = ProcessActionInput(
        session_id=test_session.id,
        action="고블린을 공격한다",
        idempotency_key="test-key-001",
    )
    await use_case.execute(
        user_id=test_session.user_id,
        input_data=input_data,
    )

    # Then
    # Character repo should be called to save updated character
    assert mock_repositories["character_repository"].save.called
    saved_character = mock_repositories["character_repository"].save.call_args[
        0
    ][0]

    # Experience should be gained but no level up (50 + 30 = 80 < 100)
    assert saved_character.stats.level == 1
    assert saved_character.stats.experience == 80  # 50 + 30
    assert saved_character.stats.current_experience == 80


@pytest.mark.asyncio
async def test_process_action_with_level_up(
    mock_repositories,
    mock_llm_service,
    test_character_near_levelup,
    test_session,
):
    """경험치 획득으로 레벨업 발생 테스트."""
    # Given
    use_case = ProcessActionUseCase(
        session_repository=mock_repositories["session_repository"],
        character_repository=mock_repositories["character_repository"],
        message_repository=mock_repositories["message_repository"],
        llm_service=mock_llm_service,
        cache_service=mock_repositories["cache_service"],
        embedding_service=mock_repositories["embedding_service"],
    )

    # Mock repository responses
    mock_repositories["session_repository"].get_by_id.return_value = (
        test_session
    )
    mock_repositories["character_repository"].get_by_id.return_value = (
        test_character_near_levelup
    )
    mock_repositories["cache_service"].get.return_value = (
        None  # No cached result
    )

    # Mock LLM response with enough experience to level up
    llm_response_content = """```json
{
    "narrative": "보스를 처치했습니다!",
    "options": ["계속 진행"],
    "state_changes": {
        "experience_gained": 50
    }
}
```"""
    mock_llm_response = MagicMock()
    mock_llm_response.content = llm_response_content
    mock_llm_service.generate_context_string.return_value = "context"
    mock_llm_service.generate_response.return_value = mock_llm_response

    # When
    input_data = ProcessActionInput(
        session_id=test_session.id,
        action="보스를 공격한다",
        idempotency_key="test-key-002",
    )
    await use_case.execute(
        user_id=test_session.user_id,
        input_data=input_data,
    )

    # Then
    # Character should level up (90 + 50 = 140, requires 100 for Lv2)
    assert mock_repositories["character_repository"].save.called
    saved_character = mock_repositories["character_repository"].save.call_args[
        0
    ][0]

    assert saved_character.stats.level == 2
    assert saved_character.stats.experience == 140
    assert saved_character.stats.current_experience == 40  # 140 - 100
    assert saved_character.stats.max_hp == 110  # 100 + 10
    assert saved_character.stats.hp == 110  # Full heal on level up
