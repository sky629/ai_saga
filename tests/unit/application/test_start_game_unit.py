from unittest.mock import AsyncMock, MagicMock

import pytest

from app.common.utils.datetime import get_utc_datetime
from app.common.utils.id_generator import get_uuid7
from app.game.application.use_cases.start_game import (
    StartGameInput,
    StartGameUseCase,
)
from app.game.domain.entities import CharacterEntity, ScenarioEntity
from app.game.domain.entities.character import CharacterProfile
from app.game.domain.value_objects import MessageRole
from config.settings import settings


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
    mock_llm_service,
):
    return StartGameUseCase(
        session_repository=mock_session_repo,
        character_repository=mock_character_repo,
        scenario_repository=mock_scenario_repo,
        message_repository=mock_message_repo,
        llm_service=mock_llm_service,
    )


@pytest.mark.asyncio
async def test_start_game_success(
    use_case,
    mock_session_repo,
    mock_character_repo,
    mock_scenario_repo,
    mock_message_repo,
    mock_llm_service,
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
        created_at=get_utc_datetime(),
    )
    mock_character_repo.get_by_id.return_value = character

    scenario = ScenarioEntity(
        id=scenario_id,
        name="좀비 아포칼립스",
        description="Desc",
        world_setting=(
            "폐허가 된 서울에서 생존자와 좀비가 뒤엉킨다. "
            "감염체는 소리와 움직임, 피 냄새에 민감하다."
        ),
        initial_location="서울 외곽 - 폐건물 2층",
        genre="survival",
        difficulty="normal",
        max_turns=30,
        is_active=True,
        created_at=get_utc_datetime(),
        updated_at=get_utc_datetime(),
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

    input_data = StartGameInput(
        character_id=character_id, scenario_id=scenario_id
    )

    # Execute
    result = await use_case.execute(user_id, input_data)

    # Verify
    assert result.character_id == character_id
    assert result.scenario_id == scenario_id

    # Verify repository calls
    mock_session_repo.save.assert_called_once()
    mock_session_repo.commit.assert_called_once()
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
    mock_llm_service,
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
        created_at=get_utc_datetime(),
    )
    mock_character_repo.get_by_id.return_value = character

    scenario = ScenarioEntity(
        id=scenario_id,
        name="좀비 아포칼립스",
        description="Desc",
        world_setting=(
            "폐허가 된 서울에서 생존자와 좀비가 뒤엉킨다. "
            "감염체는 소리와 움직임, 피 냄새에 민감하다."
        ),
        initial_location="서울 외곽 - 폐건물 2층",
        genre="survival",
        difficulty="normal",
        max_turns=30,
        is_active=True,
        created_at=get_utc_datetime(),
        updated_at=get_utc_datetime(),
    )
    mock_scenario_repo.get_by_id.return_value = scenario
    mock_session_repo.get_active_by_character.return_value = None

    async def save_side_effect(session):
        return session

    mock_session_repo.save.side_effect = save_side_effect

    # Mock LLM failure
    mock_llm_service.generate_response.side_effect = Exception("LLM Error")

    input_data = StartGameInput(
        character_id=character_id, scenario_id=scenario_id
    )

    # Execute & Verify
    with pytest.raises(Exception) as excinfo:
        await use_case.execute(user_id, input_data)

    assert str(excinfo.value) == "LLM Error"

    # Session was saved (flush only)
    mock_session_repo.save.assert_called_once()

    # Message was NOT created -> 트랜잭션 롤백 시 세션도 함께 사라짐
    mock_message_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_start_game_stores_parsed_response_when_llm_returns_json(
    use_case,
    mock_session_repo,
    mock_character_repo,
    mock_scenario_repo,
    mock_message_repo,
    mock_llm_service,
):
    """시작 메시지가 JSON 형식이면 parsed_response에 저장되어야 함."""
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
        created_at=get_utc_datetime(),
    )
    mock_character_repo.get_by_id.return_value = character

    scenario = ScenarioEntity(
        id=scenario_id,
        name="좀비 아포칼립스",
        description="Desc",
        world_setting=(
            "폐허가 된 서울에서 생존자와 좀비가 뒤엉킨다. "
            "감염체는 소리와 움직임, 피 냄새에 민감하다."
        ),
        initial_location="서울 외곽 - 폐건물 2층",
        genre="survival",
        difficulty="normal",
        max_turns=30,
        is_active=True,
        created_at=get_utc_datetime(),
        updated_at=get_utc_datetime(),
    )
    mock_scenario_repo.get_by_id.return_value = scenario
    mock_session_repo.get_active_by_character.return_value = None
    mock_session_repo.save.side_effect = lambda session: session

    mock_llm_response = MagicMock()
    mock_llm_response.content = """```json
{
    "narrative": "게임 시작 내러티브",
    "options": ["첫 행동", "두 번째 행동"],
    "dice_applied": false,
    "state_changes": {
        "location": "Start"
    }
}
```"""
    mock_llm_response.usage.total_tokens = 10
    mock_llm_service.generate_response.return_value = mock_llm_response

    input_data = StartGameInput(
        character_id=character_id, scenario_id=scenario_id
    )

    await use_case.execute(user_id, input_data)

    created_message = mock_message_repo.create.call_args[0][0]
    assert created_message.parsed_response is not None
    assert created_message.parsed_response["narrative"] == "게임 시작 내러티브"
    assert (
        created_message.parsed_response["state_changes"]["location"] == "Start"
    )


@pytest.mark.asyncio
async def test_start_game_uses_character_driven_opening_prompt(
    use_case,
    mock_session_repo,
    mock_character_repo,
    mock_scenario_repo,
    mock_message_repo,
    mock_llm_service,
):
    """시작 프롬프트와 요청 문구가 캐릭터 설정을 강하게 반영해야 함."""
    user_id = get_uuid7()
    character_id = get_uuid7()
    scenario_id = get_uuid7()

    character = CharacterEntity(
        id=character_id,
        user_id=user_id,
        scenario_id=scenario_id,
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
    mock_character_repo.get_by_id.return_value = character

    scenario = ScenarioEntity(
        id=scenario_id,
        name="용사의 여정",
        description="Desc",
        world_setting="World",
        initial_location="하늘빛 마을 - 모험가 길드 앞",
        genre="fantasy",
        difficulty="normal",
        max_turns=30,
        is_active=True,
        created_at=get_utc_datetime(),
        updated_at=get_utc_datetime(),
    )
    mock_scenario_repo.get_by_id.return_value = scenario
    mock_session_repo.get_active_by_character.return_value = None
    mock_session_repo.save.side_effect = lambda session: session

    mock_llm_response = MagicMock()
    mock_llm_response.content = "Welcome to the game."
    mock_llm_response.usage.total_tokens = 10
    mock_llm_service.generate_response.return_value = mock_llm_response

    await use_case.execute(
        user_id,
        StartGameInput(character_id=character_id, scenario_id=scenario_id),
    )

    generate_kwargs = mock_llm_service.generate_response.call_args.kwargs
    assert "## 캐릭터 핵심 설정" in generate_kwargs["system_prompt"]
    assert (
        "- 외형: 검은 단발과 오래된 흉터" in generate_kwargs["system_prompt"]
    )
    assert "- 목표: 실종된 형을 찾는 것" in generate_kwargs["system_prompt"]
    assert (
        "첫 선택지 2개 이상은 캐릭터 설정" in generate_kwargs["system_prompt"]
    )
    assert (
        generate_kwargs["messages"][0]["content"]
        == "게임을 시작합니다. 캐릭터의 목표와 외형이 자연스럽게 드러나도록 현재 상황을 묘사하고, 첫 선택지 3개 중 최소 2개는 캐릭터 설정을 직접 반영해주세요."
    )


@pytest.mark.asyncio
async def test_start_game_uses_dummy_illustration_when_feature_disabled(
    mock_session_repo,
    mock_character_repo,
    mock_scenario_repo,
    mock_message_repo,
    mock_llm_service,
):
    user_id = get_uuid7()
    character_id = get_uuid7()
    scenario_id = get_uuid7()
    image_service = AsyncMock()

    use_case = StartGameUseCase(
        session_repository=mock_session_repo,
        character_repository=mock_character_repo,
        scenario_repository=mock_scenario_repo,
        message_repository=mock_message_repo,
        llm_service=mock_llm_service,
        image_service=image_service,
    )

    character = CharacterEntity(
        id=character_id,
        user_id=user_id,
        scenario_id=scenario_id,
        name="Hero",
        description="Desc",
        stats={},
        inventory=[],
        is_active=True,
        created_at=get_utc_datetime(),
    )
    scenario = ScenarioEntity(
        id=scenario_id,
        name="좀비 아포칼립스",
        description="Desc",
        world_setting=(
            "폐허가 된 서울에서 생존자와 좀비가 뒤엉킨다. "
            "감염체는 소리와 움직임, 피 냄새에 민감하다."
        ),
        initial_location="서울 외곽 - 폐건물 2층",
        genre="survival",
        difficulty="normal",
        max_turns=30,
        is_active=True,
        created_at=get_utc_datetime(),
        updated_at=get_utc_datetime(),
    )
    mock_character_repo.get_by_id.return_value = character
    mock_scenario_repo.get_by_id.return_value = scenario
    mock_session_repo.get_active_by_character.return_value = None
    mock_session_repo.save.side_effect = lambda session: session

    mock_llm_response = MagicMock()
    mock_llm_response.content = "Welcome to the game."
    mock_llm_response.usage.total_tokens = 10
    mock_llm_service.generate_response.return_value = mock_llm_response
    image_service.generate_image.return_value = (
        "https://example.com/dummy-image.png"
    )

    original_flag = settings.image_generation_enabled
    settings.image_generation_enabled = False
    try:
        result = await use_case.execute(
            user_id,
            StartGameInput(character_id=character_id, scenario_id=scenario_id),
        )
    finally:
        settings.image_generation_enabled = original_flag

    assert result.image_url == "https://example.com/dummy-image.png"
    image_service.generate_image.assert_called_once()
    called_prompt = image_service.generate_image.call_args.kwargs["prompt"]
    assert (
        "Depict this exact story moment: Welcome to the game." in called_prompt
    )
    assert "Single-panel illustration only." in called_prompt
    assert "No readable text" in called_prompt
    assert "This must look like a clean illustration" in called_prompt
    assert "Set the scene at 서울 외곽 - 폐건물 2층." in called_prompt
    assert "The main focus is Hero." in called_prompt
    assert "zombie apocalypse" in called_prompt.lower()


@pytest.mark.asyncio
async def test_start_game_cleans_up_uploaded_image_when_message_save_fails(
    mock_session_repo,
    mock_character_repo,
    mock_scenario_repo,
    mock_message_repo,
    mock_llm_service,
):
    user_id = get_uuid7()
    character_id = get_uuid7()
    scenario_id = get_uuid7()
    image_service = AsyncMock()

    use_case = StartGameUseCase(
        session_repository=mock_session_repo,
        character_repository=mock_character_repo,
        scenario_repository=mock_scenario_repo,
        message_repository=mock_message_repo,
        llm_service=mock_llm_service,
        image_service=image_service,
    )

    character = CharacterEntity(
        id=character_id,
        user_id=user_id,
        scenario_id=scenario_id,
        name="Hero",
        description="Desc",
        stats={},
        inventory=[],
        is_active=True,
        created_at=get_utc_datetime(),
    )
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
        updated_at=get_utc_datetime(),
    )
    mock_character_repo.get_by_id.return_value = character
    mock_scenario_repo.get_by_id.return_value = scenario
    mock_session_repo.get_active_by_character.return_value = None
    mock_session_repo.save.side_effect = lambda session: session

    mock_llm_response = MagicMock()
    mock_llm_response.content = "Welcome to the game."
    mock_llm_response.usage.total_tokens = 10
    mock_llm_service.generate_response.return_value = mock_llm_response
    image_service.generate_image.return_value = (
        "https://example.com/generated-image.png"
    )
    mock_message_repo.create.side_effect = Exception("message save failed")

    with pytest.raises(Exception, match="message save failed"):
        await use_case.execute(
            user_id,
            StartGameInput(character_id=character_id, scenario_id=scenario_id),
        )

    image_service.delete_image.assert_called_once_with(
        "https://example.com/generated-image.png"
    )


@pytest.mark.asyncio
async def test_start_game_cleans_up_uploaded_image_when_commit_fails(
    mock_session_repo,
    mock_character_repo,
    mock_scenario_repo,
    mock_message_repo,
    mock_llm_service,
):
    user_id = get_uuid7()
    character_id = get_uuid7()
    scenario_id = get_uuid7()
    image_service = AsyncMock()

    use_case = StartGameUseCase(
        session_repository=mock_session_repo,
        character_repository=mock_character_repo,
        scenario_repository=mock_scenario_repo,
        message_repository=mock_message_repo,
        llm_service=mock_llm_service,
        image_service=image_service,
    )

    character = CharacterEntity(
        id=character_id,
        user_id=user_id,
        scenario_id=scenario_id,
        name="Hero",
        description="Desc",
        stats={},
        inventory=[],
        is_active=True,
        created_at=get_utc_datetime(),
    )
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
        updated_at=get_utc_datetime(),
    )
    mock_character_repo.get_by_id.return_value = character
    mock_scenario_repo.get_by_id.return_value = scenario
    mock_session_repo.get_active_by_character.return_value = None
    mock_session_repo.save.side_effect = lambda session: session
    mock_session_repo.commit.side_effect = Exception("commit failed")

    mock_llm_response = MagicMock()
    mock_llm_response.content = "Welcome to the game."
    mock_llm_response.usage.total_tokens = 10
    mock_llm_service.generate_response.return_value = mock_llm_response
    image_service.generate_image.return_value = (
        "https://example.com/generated-image.png"
    )

    with pytest.raises(Exception, match="commit failed"):
        await use_case.execute(
            user_id,
            StartGameInput(character_id=character_id, scenario_id=scenario_id),
        )

    image_service.delete_image.assert_called_once_with(
        "https://example.com/generated-image.png"
    )
