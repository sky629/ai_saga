
from app.common.utils.datetime import get_utc_datetime
from app.common.utils.id_generator import get_uuid7
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.game.application.use_cases.start_game import StartGameUseCase, StartGameInput
from app.game.domain.entities import CharacterEntity, ScenarioEntity
from app.game.domain.value_objects import MessageRole

@pytest.fixture
def mock_session_repo():
    return AsyncMock()

@pytest.fixture
def mock_character_repo():
    return AsyncMock()

@pytest.fixture
def mock_scenario_repo():
    return AsyncMock()

@pytest.fixture
def mock_message_repo():
    return AsyncMock()

@pytest.fixture
def mock_llm_service():
    return AsyncMock()

@pytest.fixture
def use_case(
    mock_session_repo,
    mock_character_repo,
    mock_scenario_repo,
    mock_message_repo,
    mock_llm_service
):
    return StartGameUseCase(
        session_repository=mock_session_repo,
        character_repository=mock_character_repo,
        scenario_repository=mock_scenario_repo,
        message_repository=mock_message_repo,
        llm_service=mock_llm_service
    )

@pytest.mark.asyncio
async def test_start_game_success(
    use_case,
    mock_session_repo,
    mock_character_repo,
    mock_scenario_repo,
    mock_message_repo,
    mock_llm_service
):
    """
    [성공 케이스]
    UseCase 실행 시:
    1. SessionRepository.save() 호출 (DB flush)
    2. LLM 응답 생성
    3. MessageRepository.create() 호출 (DB flush)
    
    모든 과정이 에러 없이 끝나면, 상위 의존성(depends)에서 commit이 실행될 것임.
    단위 테스트에서는 리포지토리 메서드가 각각 1회씩 호출되었는지 검증.
    """
    # Setup
    user_id = get_uuid7()
    character_id = get_uuid7()
    scenario_id = get_uuid7()
    
    character = CharacterEntity(
        id=character_id,
        user_id=user_id,
        scenario_id=scenario_id,
        name="Hero",
        description="Desc",
        stats={},
        inventory=[],
        is_active=True,
        created_at=get_utc_datetime()
    )
    mock_character_repo.get_by_id.return_value = character
    
    scenario = ScenarioEntity(
        id=scenario_id,
        name="Scenario",
        description="Desc",
        world_setting="World",
        initial_location="Start",
        genre="fantasy",
        difficulty="normal",
        max_turns=30,
        is_active=True,
        created_at=get_utc_datetime(),
        updated_at=get_utc_datetime()
    )
    mock_scenario_repo.get_by_id.return_value = scenario
    
    mock_session_repo.get_active_by_character.return_value = None
    
    # Mock save to return the session with ID
    async def save_side_effect(session):
        return session
    mock_session_repo.save.side_effect = save_side_effect

    # Mock LLM response
    mock_llm_response = MagicMock()
    mock_llm_response.content = "Welcome to the game."
    mock_llm_response.usage.total_tokens = 10
    mock_llm_service.generate_response.return_value = mock_llm_response

    input_data = StartGameInput(character_id=character_id, scenario_id=scenario_id)

    # Execute
    result = await use_case.execute(user_id, input_data)

    # Verify
    assert result.character_id == character_id
    assert result.scenario_id == scenario_id
    
    # Verify repository calls
    mock_session_repo.save.assert_called_once()
    mock_llm_service.generate_response.assert_called_once()
    mock_message_repo.create.assert_called_once()
    
    # Verify message content
    created_message = mock_message_repo.create.call_args[0][0]
    assert created_message.content == "Welcome to the game."
    assert created_message.role == MessageRole.ASSISTANT

@pytest.mark.asyncio
async def test_start_game_llm_failure_propagates_exception(
    use_case,
    mock_session_repo,
    mock_character_repo,
    mock_scenario_repo,
    mock_message_repo,
    mock_llm_service
):
    """
    [실패 케이스 - LLM 에러]
    UseCase 실행 중 LLM 호출에서 에러가 발생하면:
    1. SessionRepository.save()는 호출되었음 (DB flush 상태)
    2. LLM에서 Exception 발생
    3. UseCase는 예외를 catch하지 않고 그대로 전파해야 함.
    
    결과적으로 상위 의존성(depends)에서 rollback이 실행되어
    세션 생성(1번)도 취소됨. (Atomic Transaction 보장)
    """
    # Setup
    user_id = get_uuid7()
    character_id = get_uuid7()
    scenario_id = get_uuid7()
    
    character = CharacterEntity(
        id=character_id,
        user_id=user_id,
        scenario_id=scenario_id,
        name="Hero",
        description="Desc",
        stats={},
        inventory=[],
        is_active=True,
        created_at=get_utc_datetime()
    )
    mock_character_repo.get_by_id.return_value = character
    
    scenario = ScenarioEntity(
        id=scenario_id,
        name="Scenario",
        description="Desc",
        world_setting="World",
        initial_location="Start",
        genre="fantasy",
        difficulty="normal",
        max_turns=30,
        is_active=True,
        created_at=get_utc_datetime(),
        updated_at=get_utc_datetime()
    )
    mock_scenario_repo.get_by_id.return_value = scenario
    mock_session_repo.get_active_by_character.return_value = None
    
    async def save_side_effect(session):
        return session
    mock_session_repo.save.side_effect = save_side_effect

    # Mock LLM failure
    mock_llm_service.generate_response.side_effect = Exception("LLM Error")

    input_data = StartGameInput(character_id=character_id, scenario_id=scenario_id)

    # Execute & Verify
    with pytest.raises(Exception) as excinfo:
        await use_case.execute(user_id, input_data)
    
    assert str(excinfo.value) == "LLM Error"
    
    # Session was saved (flush only)
    mock_session_repo.save.assert_called_once()
    
    # Message was NOT created -> 트랜잭션 롤백 시 세션도 함께 사라짐
    mock_message_repo.create.assert_not_called()
