"""Progression 게임 타입 흐름 단위 테스트."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.common.exception import ServerError
from app.common.utils.id_generator import get_uuid7
from app.game.application.use_cases.process_action import (
    ProcessActionInput,
    ProcessActionUseCase,
)
from app.game.application.use_cases.start_game import (
    StartGameInput,
    StartGameUseCase,
)
from app.game.domain.entities import CharacterEntity, CharacterProfile
from app.game.domain.entities.game_session import GameSessionEntity
from app.game.domain.entities.scenario import ScenarioEntity
from app.game.domain.value_objects import (
    GameType,
    ScenarioDifficulty,
    ScenarioGenre,
    SessionStatus,
)


def _make_progression_scenario() -> ScenarioEntity:
    return ScenarioEntity(
        id=get_uuid7(),
        name="기연 일지",
        description="동굴 속 12개월 수련 생존기",
        world_setting="절벽 아래 신비한 동굴에서 1년간 수련한다.",
        initial_location="청색광이 감도는 거대 동굴",
        game_type=GameType.PROGRESSION,
        genre=ScenarioGenre.WUXIA,
        difficulty=ScenarioDifficulty.NORMAL,
        max_turns=12,
        tags=["무협", "수련", "기연", "동굴"],
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )


def _make_character(user_id, scenario_id) -> CharacterEntity:
    return CharacterEntity(
        id=get_uuid7(),
        user_id=user_id,
        scenario_id=scenario_id,
        name="연우",
        profile=CharacterProfile(
            age=19,
            gender="비공개",
            appearance="검은 머리의 가는 체구, 날카로운 눈매",
            goal="동굴을 탈출해 강호에 이름을 남긴다",
        ),
        inventory=[],
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_start_game_progression_initializes_game_state():
    user_id = get_uuid7()
    scenario = _make_progression_scenario()
    character = _make_character(user_id, scenario.id)

    session_repo = AsyncMock()
    session_repo.get_active_by_character.return_value = None
    session_repo.save.side_effect = lambda session: session
    character_repo = AsyncMock()
    character_repo.get_by_id.return_value = character
    scenario_repo = AsyncMock()
    scenario_repo.get_by_id.return_value = scenario
    message_repo = AsyncMock()
    llm_service = AsyncMock()

    llm_response = MagicMock()
    llm_response.content = """
```json
{
  "narrative": "신비한 동굴에서 첫 달을 맞이할 준비를 합니다.",
  "options": [
    {"label": "동굴 벽면을 관찰한다", "action_type": "progression"},
    {"label": "폭포 아래에서 기초 체련을 한다", "action_type": "progression"}
  ],
  "consumes_turn": false
}
```
"""
    llm_response.usage.total_tokens = 42
    llm_service.generate_response.return_value = llm_response

    use_case = StartGameUseCase(
        session_repository=session_repo,
        character_repository=character_repo,
        scenario_repository=scenario_repo,
        message_repository=message_repo,
        llm_service=llm_service,
    )

    await use_case.execute(
        user_id,
        StartGameInput(character_id=character.id, scenario_id=scenario.id),
    )

    saved_session = session_repo.save.call_args.args[0]
    assert saved_session.max_turns == 12
    assert saved_session.game_state["internal_power"] == 0
    assert saved_session.game_state["external_power"] == 0
    assert saved_session.game_state["hp"] == 100
    assert saved_session.game_state["manuals"] == []


@pytest.mark.asyncio
async def test_progression_question_does_not_advance_turn():
    user_id = get_uuid7()
    scenario = _make_progression_scenario()
    character = _make_character(user_id, scenario.id)
    now = datetime.now(timezone.utc)
    session = GameSessionEntity(
        id=get_uuid7(),
        user_id=user_id,
        character_id=character.id,
        scenario_id=scenario.id,
        current_location=scenario.initial_location,
        game_state={
            "hp": 100,
            "internal_power": 5,
            "external_power": 10,
            "manuals": [],
        },
        status=SessionStatus.ACTIVE,
        turn_count=0,
        max_turns=12,
        started_at=now,
        last_activity_at=now,
    )

    session_repo = AsyncMock()
    session_repo.get_by_id.return_value = session
    session_repo.save.side_effect = lambda saved: saved
    message_repo = AsyncMock()
    character_repo = AsyncMock()
    character_repo.get_by_id.return_value = character
    scenario_repo = AsyncMock()
    scenario_repo.get_by_id.return_value = scenario
    llm_service = AsyncMock()
    cache_service = AsyncMock()
    cache_service.get.return_value = None
    embedding_service = AsyncMock()

    llm_response = MagicMock()
    llm_response.content = """
```json
{
  "narrative": "동굴의 기운은 아직 완전히 읽어내지 못했지만, 북서쪽 벽면에서 냉기가 흐릅니다.",
  "options": [
    {"label": "냉기가 흐르는 벽면을 조사한다", "action_type": "progression"},
    {"label": "기운의 흐름에 대해 더 질문한다", "action_type": "question"}
  ],
  "consumes_turn": false,
  "state_changes": {}
}
```
"""
    llm_response.usage.total_tokens = 50
    llm_service.generate_response.return_value = llm_response

    use_case = ProcessActionUseCase(
        session_repository=session_repo,
        message_repository=message_repo,
        character_repository=character_repo,
        scenario_repository=scenario_repo,
        llm_service=llm_service,
        cache_service=cache_service,
        embedding_service=embedding_service,
    )

    result = await use_case.execute(
        user_id,
        ProcessActionInput(
            session_id=session.id,
            action="저 냉기는 어디서 오는 거야?",
            idempotency_key="progression-question",
        ),
    )

    assert result.response.turn_count == 0
    assert result.response.status_panel.remaining_turns == 12
    saved_session = session_repo.save.call_args.args[0]
    assert saved_session.turn_count == 0


@pytest.mark.asyncio
async def test_progression_retries_once_when_llm_response_is_malformed():
    user_id = get_uuid7()
    scenario = _make_progression_scenario()
    character = _make_character(user_id, scenario.id)
    now = datetime.now(timezone.utc)
    session = GameSessionEntity(
        id=get_uuid7(),
        user_id=user_id,
        character_id=character.id,
        scenario_id=scenario.id,
        current_location=scenario.initial_location,
        game_state={
            "hp": 100,
            "max_hp": 100,
            "internal_power": 12,
            "external_power": 8,
            "manuals": [],
        },
        status=SessionStatus.ACTIVE,
        turn_count=2,
        max_turns=12,
        started_at=now,
        last_activity_at=now,
    )

    session_repo = AsyncMock()
    session_repo.get_by_id.return_value = session
    session_repo.save.side_effect = lambda saved: saved
    message_repo = AsyncMock()
    character_repo = AsyncMock()
    character_repo.get_by_id.return_value = character
    scenario_repo = AsyncMock()
    scenario_repo.get_by_id.return_value = scenario
    llm_service = AsyncMock()
    cache_service = AsyncMock()
    cache_service.get.return_value = None
    embedding_service = AsyncMock()
    image_service = AsyncMock()
    image_service.generate_image.return_value = "https://example.com/retry.png"

    malformed_response = MagicMock()
    malformed_response.content = """
```json
{
  "narrative": "한 달 동안 동굴 안쪽을 탐색했지만, 아직 결론을 내리기엔 이르다.",
  "options": [],
  "consumes_turn": true,
  "state_changes": {
    "internal_power_delta": 1
  }
}
```
"""
    malformed_response.usage.total_tokens = 40

    repaired_response = MagicMock()
    repaired_response.content = """
```json
{
  "narrative": "한 달 동안 동굴 안쪽을 탐색한 끝에, 북쪽 석벽 뒤로 흐르는 바람길을 찾아냈습니다.",
  "options": [
    {"label": "바람길 끝을 더듬어 들어간다", "action_type": "progression"},
    {"label": "석벽 주변의 흔적을 다시 조사한다", "action_type": "progression"}
  ],
  "consumes_turn": true,
  "image_focus": "북쪽 석벽의 틈새에서 바람길을 발견한 젊은 무인",
  "state_changes": {
    "internal_power_delta": 1
  }
}
```
"""
    repaired_response.usage.total_tokens = 52
    llm_service.generate_response.side_effect = [
        malformed_response,
        repaired_response,
    ]

    use_case = ProcessActionUseCase(
        session_repository=session_repo,
        message_repository=message_repo,
        character_repository=character_repo,
        scenario_repository=scenario_repo,
        llm_service=llm_service,
        cache_service=cache_service,
        embedding_service=embedding_service,
        image_service=image_service,
    )

    result = await use_case.execute(
        user_id,
        ProcessActionInput(
            session_id=session.id,
            action="한 달 동안 동굴 북쪽 석벽을 탐색한다",
            action_type="progression",
            idempotency_key="progression-malformed-retry",
        ),
    )

    assert llm_service.generate_response.await_count == 2
    assert [option.label for option in result.response.options] == [
        "바람길 끝을 더듬어 들어간다",
        "석벽 주변의 흔적을 다시 조사한다",
    ]
    assert result.response.image_url == "https://example.com/retry.png"


@pytest.mark.asyncio
async def test_progression_rejects_generic_progression_options():
    user_id = get_uuid7()
    scenario = _make_progression_scenario()
    character = _make_character(user_id, scenario.id)
    now = datetime.now(timezone.utc)
    session = GameSessionEntity(
        id=get_uuid7(),
        user_id=user_id,
        character_id=character.id,
        scenario_id=scenario.id,
        current_location=scenario.initial_location,
        game_state={
            "hp": 42,
            "max_hp": 100,
            "internal_power": 15,
            "external_power": 24,
            "manuals": [
                {
                    "name": "용권신장 (龍拳神掌)",
                    "category": "external",
                    "mastery": 75,
                    "aura": "fierce",
                }
            ],
        },
        status=SessionStatus.ACTIVE,
        turn_count=3,
        max_turns=12,
        started_at=now,
        last_activity_at=now,
    )

    session_repo = AsyncMock()
    session_repo.get_by_id.return_value = session
    session_repo.save.side_effect = lambda saved: saved
    message_repo = AsyncMock()
    character_repo = AsyncMock()
    character_repo.get_by_id.return_value = character
    scenario_repo = AsyncMock()
    scenario_repo.get_by_id.return_value = scenario
    llm_service = AsyncMock()
    cache_service = AsyncMock()
    cache_service.get.return_value = None
    embedding_service = AsyncMock()
    image_service = AsyncMock()
    image_service.generate_image.return_value = (
        "https://example.com/progression-month4.png"
    )

    llm_response = MagicMock()
    llm_response.content = """
```json
{
  "narrative": "'용권신장'은 지난 달 수련으로 숙련도가 110에 달했습니다.\\n\\n* **절벽 틈새를 탐색한다:** 다음 기연의 실마리를 찾는다.\\n* **청광심법을 다듬는다:** 흔들린 호흡을 다시 고른다.",
  "options": [
    {"label": "다음 행동", "action_type": "progression"}
  ],
  "consumes_turn": true,
  "image_focus": "절벽 아래에서 권법을 마무리한 젊은 무인",
  "state_changes": {
    "manual_mastery_updates": [
      {
        "name": "용권신장 (龍拳神掌)",
        "mastery_delta": 5
      }
    ]
  }
}
```
"""
    llm_response.usage.total_tokens = 60
    llm_service.generate_response.return_value = llm_response

    use_case = ProcessActionUseCase(
        session_repository=session_repo,
        message_repository=message_repo,
        character_repository=character_repo,
        scenario_repository=scenario_repo,
        llm_service=llm_service,
        cache_service=cache_service,
        embedding_service=embedding_service,
        image_service=image_service,
    )

    with pytest.raises(ServerError):
        await use_case.execute(
            user_id,
            ProcessActionInput(
                session_id=session.id,
                action="한 달 동안 용권신장을 연마한다",
                action_type="progression",
                idempotency_key="progression-invalid-generic-option",
            ),
        )

    session_repo.save.assert_not_called()
    image_service.generate_image.assert_not_called()


@pytest.mark.asyncio
async def test_progression_question_rejects_growth_payload():
    user_id = get_uuid7()
    scenario = _make_progression_scenario()
    character = _make_character(user_id, scenario.id)
    now = datetime.now(timezone.utc)
    session = GameSessionEntity(
        id=get_uuid7(),
        user_id=user_id,
        character_id=character.id,
        scenario_id=scenario.id,
        current_location=scenario.initial_location,
        game_state={
            "hp": 22,
            "max_hp": 100,
            "internal_power": 85,
            "external_power": 35,
            "manuals": [
                {
                    "name": "청광진기 (靑光眞氣)",
                    "category": "internal",
                    "mastery": 95,
                    "aura": "neutral",
                },
                {
                    "name": "용권신장 (龍拳神掌)",
                    "category": "external",
                    "mastery": 75,
                    "aura": "fierce",
                },
            ],
        },
        status=SessionStatus.ACTIVE,
        turn_count=9,
        max_turns=12,
        started_at=now,
        last_activity_at=now,
    )

    session_repo = AsyncMock()
    session_repo.get_by_id.return_value = session
    session_repo.save.side_effect = lambda saved: saved
    message_repo = AsyncMock()
    character_repo = AsyncMock()
    character_repo.get_by_id.return_value = character
    scenario_repo = AsyncMock()
    scenario_repo.get_by_id.return_value = scenario
    llm_service = AsyncMock()
    cache_service = AsyncMock()
    cache_service.get.return_value = None
    embedding_service = AsyncMock()
    image_service = AsyncMock()

    llm_response = MagicMock()
    llm_response.content = """
```json
{
  "narrative": "'용권신장'은 이미 지난 달 수련으로 완숙의 경지에 이르러 숙련도가 110에 달했습니다.\\n\\n* **약초 및 영과 탐색:** 체력을 회복할 실마리를 찾는다.\\n* **폭포수 아래 명상:** 호흡을 다듬으며 상처를 추스른다.",
  "options": [
    {"label": "다음 행동", "action_type": "progression"}
  ],
  "consumes_turn": false,
  "state_changes": {
    "manual_mastery_updates": [
      {
        "name": "용권신장 (龍拳神掌)",
        "mastery_delta": 5
      }
    ]
  }
}
```
"""
    llm_response.usage.total_tokens = 70
    llm_service.generate_response.return_value = llm_response

    use_case = ProcessActionUseCase(
        session_repository=session_repo,
        message_repository=message_repo,
        character_repository=character_repo,
        scenario_repository=scenario_repo,
        llm_service=llm_service,
        cache_service=cache_service,
        embedding_service=embedding_service,
        image_service=image_service,
    )

    with pytest.raises(ServerError):
        await use_case.execute(
            user_id,
            ProcessActionInput(
                session_id=session.id,
                action="용권신장 숙련도가 얼마나 돼?",
                action_type="question",
                idempotency_key="progression-question-growth-rejected",
            ),
        )

    session_repo.save.assert_not_called()


@pytest.mark.asyncio
async def test_progression_training_advances_turn_and_updates_state():
    user_id = get_uuid7()
    scenario = _make_progression_scenario()
    character = _make_character(user_id, scenario.id)
    now = datetime.now(timezone.utc)
    session = GameSessionEntity(
        id=get_uuid7(),
        user_id=user_id,
        character_id=character.id,
        scenario_id=scenario.id,
        current_location=scenario.initial_location,
        game_state={
            "hp": 100,
            "internal_power": 5,
            "external_power": 10,
            "manuals": [],
        },
        status=SessionStatus.ACTIVE,
        turn_count=0,
        max_turns=12,
        started_at=now,
        last_activity_at=now,
    )

    session_repo = AsyncMock()
    session_repo.get_by_id.return_value = session
    session_repo.save.side_effect = lambda saved: saved
    message_repo = AsyncMock()
    character_repo = AsyncMock()
    character_repo.get_by_id.return_value = character
    scenario_repo = AsyncMock()
    scenario_repo.get_by_id.return_value = scenario
    llm_service = AsyncMock()
    cache_service = AsyncMock()
    cache_service.get.return_value = None
    embedding_service = AsyncMock()
    image_service = AsyncMock()
    image_service.generate_image.return_value = (
        "https://example.com/month1.png"
    )

    llm_response = MagicMock()
    llm_response.content = """
```json
{
  "narrative": "한 달 동안 폭포수 아래에서 단련한 끝에 몸의 축이 단단해집니다.",
  "options": [
    {"label": "동굴 깊숙한 곳을 탐색한다", "action_type": "progression"},
    {"label": "얻은 호흡법을 되새기며 좌선한다", "action_type": "progression"}
  ],
  "consumes_turn": true,
  "image_focus": "폭포수 아래에서 수련하는 젊은 무인",
  "state_changes": {
    "hp_change": -8,
    "internal_power_delta": 2,
    "external_power_delta": 4,
    "manuals_gained": [
      {
        "name": "천잠신공",
        "category": "internal",
        "mastery": 5,
        "aura": "azure"
      }
    ],
    "manual_mastery_updates": []
  }
}
```
"""
    llm_response.usage.total_tokens = 70
    llm_service.generate_response.return_value = llm_response

    use_case = ProcessActionUseCase(
        session_repository=session_repo,
        message_repository=message_repo,
        character_repository=character_repo,
        scenario_repository=scenario_repo,
        llm_service=llm_service,
        cache_service=cache_service,
        embedding_service=embedding_service,
        image_service=image_service,
    )

    result = await use_case.execute(
        user_id,
        ProcessActionInput(
            session_id=session.id,
            action="한 달 동안 폭포 아래에서 신체를 단련한다",
            idempotency_key="progression-month-1",
        ),
    )

    assert result.response.turn_count == 1
    assert result.response.image_url == "https://example.com/month1.png"
    assert result.response.status_panel.internal_power == 7
    assert result.response.status_panel.external_power == 14
    assert result.response.status_panel.remaining_turns == 11

    saved_session = session_repo.save.call_args.args[0]
    assert saved_session.turn_count == 1
    assert saved_session.game_state["hp"] == 92
    assert saved_session.game_state["manuals"][0]["name"] == "천잠신공"


@pytest.mark.asyncio
async def test_progression_hp_heal_applies_full_positive_delta_up_to_max_hp():
    user_id = get_uuid7()
    scenario = _make_progression_scenario()
    character = _make_character(user_id, scenario.id)
    now = datetime.now(timezone.utc)
    session = GameSessionEntity(
        id=get_uuid7(),
        user_id=user_id,
        character_id=character.id,
        scenario_id=scenario.id,
        current_location=scenario.initial_location,
        game_state={
            "hp": 40,
            "max_hp": 100,
            "internal_power": 0,
            "external_power": 0,
            "manuals": [],
        },
        status=SessionStatus.ACTIVE,
        turn_count=0,
        max_turns=12,
        started_at=now,
        last_activity_at=now,
    )

    session_repo = AsyncMock()
    session_repo.get_by_id.return_value = session
    session_repo.save.side_effect = lambda saved: saved
    message_repo = AsyncMock()
    character_repo = AsyncMock()
    character_repo.get_by_id.return_value = character
    scenario_repo = AsyncMock()
    scenario_repo.get_by_id.return_value = scenario
    llm_service = AsyncMock()
    cache_service = AsyncMock()
    cache_service.get.return_value = None
    embedding_service = AsyncMock()

    llm_response = MagicMock()
    llm_response.content = """
```json
{
  "narrative": "그대는 영약을 삼키고 기혈을 정돈하며 한 달간 몸을 회복했습니다.",
  "options": [
    {"label": "다음 달엔 동굴 깊은 곳을 탐색한다", "action_type": "progression"}
  ],
  "consumes_turn": true,
  "state_changes": {
    "hp_change": 45
  }
}
```
"""
    llm_response.usage.total_tokens = 40
    llm_service.generate_response.return_value = llm_response

    use_case = ProcessActionUseCase(
        session_repository=session_repo,
        message_repository=message_repo,
        character_repository=character_repo,
        scenario_repository=scenario_repo,
        llm_service=llm_service,
        cache_service=cache_service,
        embedding_service=embedding_service,
    )

    result = await use_case.execute(
        user_id,
        ProcessActionInput(
            session_id=session.id,
            action="한 달 동안 영약으로 몸을 회복한다",
            idempotency_key="progression-heal-45",
        ),
    )

    assert result.response.status_panel.hp == 85
    saved_session = session_repo.save.call_args.args[0]
    assert saved_session.game_state["hp"] == 85


@pytest.mark.asyncio
async def test_progression_infers_manual_gain_from_narrative_when_missing_state_changes():
    user_id = get_uuid7()
    scenario = _make_progression_scenario()
    character = _make_character(user_id, scenario.id)
    now = datetime.now(timezone.utc)
    session = GameSessionEntity(
        id=get_uuid7(),
        user_id=user_id,
        character_id=character.id,
        scenario_id=scenario.id,
        current_location=scenario.initial_location,
        game_state={
            "hp": 100,
            "internal_power": 5,
            "external_power": 10,
            "manuals": [],
        },
        status=SessionStatus.ACTIVE,
        turn_count=0,
        max_turns=12,
        started_at=now,
        last_activity_at=now,
    )

    session_repo = AsyncMock()
    session_repo.get_by_id.return_value = session
    session_repo.save.side_effect = lambda saved: saved
    message_repo = AsyncMock()
    character_repo = AsyncMock()
    character_repo.get_by_id.return_value = character
    scenario_repo = AsyncMock()
    scenario_repo.get_by_id.return_value = scenario
    llm_service = AsyncMock()
    cache_service = AsyncMock()
    cache_service.get.return_value = None
    embedding_service = AsyncMock()

    llm_response = MagicMock()
    llm_response.content = """
```json
{
  "narrative": "그대는 청색 광맥 주변의 바위 틈새를 샅샅이 뒤진 끝에 '청룡심법(靑龍心法)'이라 적힌 무림비급을 발견했습니다. 이는 한 달간의 탐색 끝에 얻은 귀한 기연입니다.",
  "options": [
    {"label": "청룡심법을 펼쳐 구결을 읽는다", "action_type": "progression"}
  ],
  "consumes_turn": true,
  "state_changes": {
    "internal_power_delta": 2,
    "external_power_delta": 1
  }
}
```
"""
    llm_response.usage.total_tokens = 60
    llm_service.generate_response.return_value = llm_response

    use_case = ProcessActionUseCase(
        session_repository=session_repo,
        message_repository=message_repo,
        character_repository=character_repo,
        scenario_repository=scenario_repo,
        llm_service=llm_service,
        cache_service=cache_service,
        embedding_service=embedding_service,
    )

    result = await use_case.execute(
        user_id,
        ProcessActionInput(
            session_id=session.id,
            action="한 달 동안 청색 광맥 주변을 탐색한다",
            idempotency_key="progression-manual-inference",
        ),
    )

    assert result.response.status_panel.manuals[0].name == "청룡심법(靑龍心法)"
    saved_session = session_repo.save.call_args.args[0]
    assert (
        saved_session.game_state["manuals"][0]["name"] == "청룡심법(靑龍心法)"
    )
    created_message = message_repo.create.call_args_list[-1].args[0]
    assert (
        created_message.parsed_response["state_changes"]["manuals_gained"][0][
            "name"
        ]
        == "청룡심법(靑龍心法)"
    )


@pytest.mark.asyncio
async def test_progression_infers_shinjang_manual_from_narrative():
    user_id = get_uuid7()
    scenario = _make_progression_scenario()
    character = _make_character(user_id, scenario.id)
    now = datetime.now(timezone.utc)
    session = GameSessionEntity(
        id=get_uuid7(),
        user_id=user_id,
        character_id=character.id,
        scenario_id=scenario.id,
        current_location=scenario.initial_location,
        game_state={
            "hp": 100,
            "internal_power": 5,
            "external_power": 10,
            "manuals": [],
        },
        status=SessionStatus.ACTIVE,
        turn_count=0,
        max_turns=12,
        started_at=now,
        last_activity_at=now,
    )

    session_repo = AsyncMock()
    session_repo.get_by_id.return_value = session
    session_repo.save.side_effect = lambda saved: saved
    message_repo = AsyncMock()
    character_repo = AsyncMock()
    character_repo.get_by_id.return_value = character
    scenario_repo = AsyncMock()
    scenario_repo.get_by_id.return_value = scenario
    llm_service = AsyncMock()
    cache_service = AsyncMock()
    cache_service.get.return_value = None
    embedding_service = AsyncMock()

    llm_response = MagicMock()
    llm_response.content = """
```json
{
  "narrative": "그대는 절벽 벽면의 갈라진 틈 사이에서 벽영신장의 구결이 적힌 낡은 비급을 손에 넣었다.",
  "options": [
    {"label": "벽영신장의 초식을 익혀 본다", "action_type": "progression"}
  ],
  "consumes_turn": true,
  "state_changes": {
    "internal_power_delta": 1,
    "external_power_delta": 3
  }
}
```
"""
    llm_response.usage.total_tokens = 60
    llm_service.generate_response.return_value = llm_response

    use_case = ProcessActionUseCase(
        session_repository=session_repo,
        message_repository=message_repo,
        character_repository=character_repo,
        scenario_repository=scenario_repo,
        llm_service=llm_service,
        cache_service=cache_service,
        embedding_service=embedding_service,
    )

    result = await use_case.execute(
        user_id,
        ProcessActionInput(
            session_id=session.id,
            action="한 달 동안 절벽 벽면의 숨겨진 틈을 탐색한다",
            idempotency_key="progression-shinjang-inference",
        ),
    )

    assert result.response.status_panel.manuals[0].name == "벽영신장"
    assert result.response.status_panel.manuals[0].category == "external"

    saved_session = session_repo.save.call_args.args[0]
    assert saved_session.game_state["manuals"][0]["name"] == "벽영신장"
    assert saved_session.game_state["manuals"][0]["category"] == "external"

    created_message = message_repo.create.call_args_list[-1].args[0]
    assert (
        created_message.parsed_response["state_changes"]["manuals_gained"][0][
            "name"
        ]
        == "벽영신장"
    )


@pytest.mark.asyncio
async def test_progression_updates_internal_manual_mastery_from_training_intent():
    user_id = get_uuid7()
    scenario = _make_progression_scenario()
    character = _make_character(user_id, scenario.id)
    now = datetime.now(timezone.utc)
    session = GameSessionEntity(
        id=get_uuid7(),
        user_id=user_id,
        character_id=character.id,
        scenario_id=scenario.id,
        current_location=scenario.initial_location,
        game_state={
            "hp": 100,
            "internal_power": 12,
            "external_power": 10,
            "manuals": [
                {
                    "name": "청룡심법(靑龍心法)",
                    "category": "internal",
                    "mastery": 5,
                    "aura": "azure",
                }
            ],
        },
        status=SessionStatus.ACTIVE,
        turn_count=1,
        max_turns=12,
        started_at=now,
        last_activity_at=now,
    )

    session_repo = AsyncMock()
    session_repo.get_by_id.return_value = session
    session_repo.save.side_effect = lambda saved: saved
    message_repo = AsyncMock()
    character_repo = AsyncMock()
    character_repo.get_by_id.return_value = character
    scenario_repo = AsyncMock()
    scenario_repo.get_by_id.return_value = scenario
    llm_service = AsyncMock()
    cache_service = AsyncMock()
    cache_service.get.return_value = None
    embedding_service = AsyncMock()

    llm_response = MagicMock()
    llm_response.content = """
```json
{
  "narrative": "그대는 한 달 내내 좌선하며 단전에 흐르는 기운을 다잡았고, 청룡심법의 맥을 조금 더 이해하게 되었습니다.",
  "options": [
    {"label": "다음 달에도 심법 수련을 이어간다", "action_type": "progression"}
  ],
  "consumes_turn": true,
  "state_changes": {
    "internal_power_delta": 3
  }
}
```
"""
    llm_response.usage.total_tokens = 55
    llm_service.generate_response.return_value = llm_response

    use_case = ProcessActionUseCase(
        session_repository=session_repo,
        message_repository=message_repo,
        character_repository=character_repo,
        scenario_repository=scenario_repo,
        llm_service=llm_service,
        cache_service=cache_service,
        embedding_service=embedding_service,
    )

    result = await use_case.execute(
        user_id,
        ProcessActionInput(
            session_id=session.id,
            action="한 달 동안 심법을 수련한다",
            idempotency_key="progression-manual-mastery",
        ),
    )

    assert result.response.status_panel.manuals[0].mastery == 10
    created_message = message_repo.create.call_args_list[-1].args[0]
    assert (
        created_message.parsed_response["state_changes"][
            "manual_mastery_updates"
        ][0]["name"]
        == "청룡심법(靑龍心法)"
    )


@pytest.mark.asyncio
async def test_progression_replaces_zero_mastery_update_with_inferred_growth():
    user_id = get_uuid7()
    scenario = _make_progression_scenario()
    character = _make_character(user_id, scenario.id)
    now = datetime.now(timezone.utc)
    session = GameSessionEntity(
        id=get_uuid7(),
        user_id=user_id,
        character_id=character.id,
        scenario_id=scenario.id,
        current_location=scenario.initial_location,
        game_state={
            "hp": 100,
            "internal_power": 12,
            "external_power": 10,
            "manuals": [
                {
                    "name": "청룡심법(靑龍心法)",
                    "category": "internal",
                    "mastery": 5,
                    "aura": "azure",
                }
            ],
        },
        status=SessionStatus.ACTIVE,
        turn_count=1,
        max_turns=12,
        started_at=now,
        last_activity_at=now,
    )

    session_repo = AsyncMock()
    session_repo.get_by_id.return_value = session
    session_repo.save.side_effect = lambda saved: saved
    message_repo = AsyncMock()
    character_repo = AsyncMock()
    character_repo.get_by_id.return_value = character
    scenario_repo = AsyncMock()
    scenario_repo.get_by_id.return_value = scenario
    llm_service = AsyncMock()
    cache_service = AsyncMock()
    cache_service.get.return_value = None
    embedding_service = AsyncMock()

    llm_response = MagicMock()
    llm_response.content = """
```json
{
  "narrative": "그대는 좌선을 이어가며 청룡심법의 구결을 더욱 깊이 체득했습니다.",
  "options": [
    {"label": "다음 달에도 심법 수련을 이어간다", "action_type": "progression"}
  ],
  "consumes_turn": true,
  "state_changes": {
    "internal_power_delta": 2,
    "manual_mastery_updates": [
      {
        "name": "청룡심법(靑龍心法)",
        "mastery_delta": 0
      }
    ]
  }
}
```
"""
    llm_response.usage.total_tokens = 55
    llm_service.generate_response.return_value = llm_response

    use_case = ProcessActionUseCase(
        session_repository=session_repo,
        message_repository=message_repo,
        character_repository=character_repo,
        scenario_repository=scenario_repo,
        llm_service=llm_service,
        cache_service=cache_service,
        embedding_service=embedding_service,
    )

    result = await use_case.execute(
        user_id,
        ProcessActionInput(
            session_id=session.id,
            action="한 달 동안 심법을 수련한다",
            idempotency_key="progression-zero-mastery-inference",
        ),
    )

    assert result.response.status_panel.manuals[0].mastery == 10
    created_message = message_repo.create.call_args_list[-1].args[0]
    assert (
        created_message.parsed_response["state_changes"][
            "manual_mastery_updates"
        ][0]["mastery_delta"]
        == 5
    )


@pytest.mark.asyncio
async def test_progression_reclassifies_unknown_manual_category_from_name():
    user_id = get_uuid7()
    scenario = _make_progression_scenario()
    character = _make_character(user_id, scenario.id)
    now = datetime.now(timezone.utc)
    session = GameSessionEntity(
        id=get_uuid7(),
        user_id=user_id,
        character_id=character.id,
        scenario_id=scenario.id,
        current_location=scenario.initial_location,
        game_state={
            "hp": 100,
            "max_hp": 100,
            "internal_power": 0,
            "external_power": 0,
            "manuals": [],
        },
        status=SessionStatus.ACTIVE,
        turn_count=2,
        max_turns=12,
        started_at=now,
        last_activity_at=now,
    )

    session_repo = AsyncMock()
    session_repo.get_by_id.return_value = session
    session_repo.save.side_effect = lambda saved: saved
    message_repo = AsyncMock()
    character_repo = AsyncMock()
    character_repo.get_by_id.return_value = character
    scenario_repo = AsyncMock()
    scenario_repo.get_by_id.return_value = scenario
    llm_service = AsyncMock()
    cache_service = AsyncMock()
    cache_service.get.return_value = None
    embedding_service = AsyncMock()

    llm_response = MagicMock()
    llm_response.content = """
```json
{
  "narrative": "하하는 동굴 틈 사이에서 청광심법의 구결이 적힌 비단 두루마리를 건져 올렸다.",
  "options": [
    {"label": "청광심법을 펼쳐 본다", "action_type": "progression"}
  ],
  "consumes_turn": true,
  "state_changes": {
    "manuals_gained": [
      {
        "name": "청광심법",
        "category": "unknown",
        "mastery": 5
      }
    ]
  }
}
```
"""
    llm_response.usage.total_tokens = 35
    llm_service.generate_response.return_value = llm_response

    use_case = ProcessActionUseCase(
        session_repository=session_repo,
        message_repository=message_repo,
        character_repository=character_repo,
        scenario_repository=scenario_repo,
        llm_service=llm_service,
        cache_service=cache_service,
        embedding_service=embedding_service,
    )

    result = await use_case.execute(
        user_id,
        ProcessActionInput(
            session_id=session.id,
            action="한 달 동안 청광심법을 살핀다",
            idempotency_key="progression-category-normalize",
        ),
    )

    assert result.response.status_panel.manuals[0].category == "internal"


@pytest.mark.asyncio
async def test_progression_reclassifies_qi_and_movement_manual_categories():
    user_id = get_uuid7()
    scenario = _make_progression_scenario()
    character = _make_character(user_id, scenario.id)
    now = datetime.now(timezone.utc)
    session = GameSessionEntity(
        id=get_uuid7(),
        user_id=user_id,
        character_id=character.id,
        scenario_id=scenario.id,
        current_location=scenario.initial_location,
        game_state={
            "hp": 100,
            "max_hp": 100,
            "internal_power": 10,
            "external_power": 6,
            "manuals": [],
        },
        status=SessionStatus.ACTIVE,
        turn_count=1,
        max_turns=12,
        started_at=now,
        last_activity_at=now,
    )

    session_repo = AsyncMock()
    session_repo.get_by_id.return_value = session
    session_repo.save.side_effect = lambda saved: saved
    message_repo = AsyncMock()
    character_repo = AsyncMock()
    character_repo.get_by_id.return_value = character
    scenario_repo = AsyncMock()
    scenario_repo.get_by_id.return_value = scenario
    llm_service = AsyncMock()
    cache_service = AsyncMock()
    cache_service.get.return_value = None
    embedding_service = AsyncMock()

    llm_response = MagicMock()
    llm_response.content = """
```json
{
  "narrative": "하하는 광맥 틈새에서 청광진기와 유영신법의 파편을 얻었다.",
  "options": [
    {"label": "한 달 동안 청광진기를 익힌다", "action_type": "progression"}
  ],
  "consumes_turn": true,
  "state_changes": {
    "manuals_gained": [
      {"name": "청광진기", "category": "unknown", "mastery": 10},
      {"name": "유영신법", "category": "unknown", "mastery": 10}
    ]
  }
}
```
"""
    llm_response.usage.total_tokens = 70
    llm_service.generate_response.return_value = llm_response

    use_case = ProcessActionUseCase(
        session_repository=session_repo,
        message_repository=message_repo,
        character_repository=character_repo,
        scenario_repository=scenario_repo,
        llm_service=llm_service,
        cache_service=cache_service,
        embedding_service=embedding_service,
    )

    result = await use_case.execute(
        user_id,
        ProcessActionInput(
            session_id=session.id,
            action="한 달 동안 청광진기와 유영신법을 살핀다",
            idempotency_key="progression-category-normalize-qi-move",
        ),
    )

    assert result.response.status_panel.manuals[0].category == "internal"
    assert result.response.status_panel.manuals[1].category == "movement"


@pytest.mark.asyncio
async def test_progression_normalizes_object_traits_gained_to_strings():
    user_id = get_uuid7()
    scenario = _make_progression_scenario()
    character = _make_character(user_id, scenario.id)
    now = datetime.now(timezone.utc)
    session = GameSessionEntity(
        id=get_uuid7(),
        user_id=user_id,
        character_id=character.id,
        scenario_id=scenario.id,
        current_location=scenario.initial_location,
        game_state={
            "hp": 100,
            "max_hp": 100,
            "internal_power": 10,
            "external_power": 6,
            "manuals": [],
            "traits": [],
        },
        status=SessionStatus.ACTIVE,
        turn_count=1,
        max_turns=12,
        started_at=now,
        last_activity_at=now,
    )

    session_repo = AsyncMock()
    session_repo.get_by_id.return_value = session
    session_repo.save.side_effect = lambda saved: saved
    message_repo = AsyncMock()
    character_repo = AsyncMock()
    character_repo.get_by_id.return_value = character
    scenario_repo = AsyncMock()
    scenario_repo.get_by_id.return_value = scenario
    llm_service = AsyncMock()
    cache_service = AsyncMock()
    cache_service.get.return_value = None
    embedding_service = AsyncMock()

    llm_response = MagicMock()
    llm_response.content = """
```json
{
  "narrative": "하하는 청색 광맥의 미세한 떨림을 읽어내며 감각이 예민해졌다.",
  "options": [
    {"label": "광맥의 흐름을 더 탐색한다", "action_type": "progression"}
  ],
  "consumes_turn": true,
  "state_changes": {
    "traits_gained": [
      {
        "name": "광맥 기운 감응",
        "description": "광맥의 미세한 흐름에 민감해진다."
      }
    ]
  }
}
```
"""
    llm_response.usage.total_tokens = 60
    llm_service.generate_response.return_value = llm_response

    use_case = ProcessActionUseCase(
        session_repository=session_repo,
        message_repository=message_repo,
        character_repository=character_repo,
        scenario_repository=scenario_repo,
        llm_service=llm_service,
        cache_service=cache_service,
        embedding_service=embedding_service,
    )

    result = await use_case.execute(
        user_id,
        ProcessActionInput(
            session_id=session.id,
            action="한 달 동안 광맥의 기운을 탐색한다",
            idempotency_key="progression-trait-object-normalize",
        ),
    )

    assert (
        "광맥 기운 감응"
        in result.response.message.parsed_response.state_changes.traits_gained
    )
    saved_session = session_repo.save.call_args.args[0]
    assert "광맥 기운 감응" in saved_session.game_state["traits"]


@pytest.mark.asyncio
async def test_progression_hp_zero_triggers_immediate_defeat_ending():
    user_id = get_uuid7()
    scenario = _make_progression_scenario()
    character = _make_character(user_id, scenario.id)
    now = datetime.now(timezone.utc)
    session = GameSessionEntity(
        id=get_uuid7(),
        user_id=user_id,
        character_id=character.id,
        scenario_id=scenario.id,
        current_location=scenario.initial_location,
        game_state={
            "hp": 10,
            "max_hp": 100,
            "internal_power": 6,
            "external_power": 4,
            "manuals": [],
        },
        status=SessionStatus.ACTIVE,
        turn_count=3,
        max_turns=12,
        started_at=now,
        last_activity_at=now,
    )

    session_repo = AsyncMock()
    session_repo.get_by_id.return_value = session
    session_repo.save.side_effect = lambda saved: saved
    message_repo = AsyncMock()
    character_repo = AsyncMock()
    character_repo.get_by_id.return_value = character
    scenario_repo = AsyncMock()
    scenario_repo.get_by_id.return_value = scenario
    llm_service = AsyncMock()
    cache_service = AsyncMock()
    cache_service.get.return_value = None
    embedding_service = AsyncMock()
    image_service = AsyncMock()
    image_service.generate_image.side_effect = [
        "https://example.com/month4.png",
        "https://example.com/final-board.png",
    ]

    llm_response = MagicMock()
    llm_response.content = """
```json
{
  "narrative": "무너지는 동굴벽을 피하려다 전신이 크게 찢기고, 숨이 끊어질 듯한 고통이 밀려옵니다.",
  "options": [
    {"label": "버티며 정신을 붙잡는다", "action_type": "progression"}
  ],
  "consumes_turn": true,
  "image_focus": "붕괴하는 동굴에서 치명상을 입은 무인",
  "state_changes": {
    "hp_change": -15,
    "internal_power_delta": 1
  }
}
```
"""
    llm_response.usage.total_tokens = 70
    llm_service.generate_response.return_value = llm_response

    use_case = ProcessActionUseCase(
        session_repository=session_repo,
        message_repository=message_repo,
        character_repository=character_repo,
        scenario_repository=scenario_repo,
        llm_service=llm_service,
        cache_service=cache_service,
        embedding_service=embedding_service,
        image_service=image_service,
    )

    result = await use_case.execute(
        user_id,
        ProcessActionInput(
            session_id=session.id,
            action="한 달 동안 무너지는 동굴을 돌파하려 한다",
            idempotency_key="progression-hp-zero-ending",
        ),
    )

    assert result.response.ending_type == "defeat"
    assert result.response.total_turns == 4
    assert (
        result.response.final_outcome.image_url
        == "https://example.com/final-board.png"
    )
    assert result.response.final_outcome.achievement_board.escaped is False
    assert (
        "탈출 실패" in result.response.final_outcome.achievement_board.summary
    )

    saved_session = session_repo.save.call_args.args[0]
    assert saved_session.status == SessionStatus.COMPLETED
    assert saved_session.game_state["hp"] == 0
    assert saved_session.game_state["final_outcome"]["ending_type"] == "defeat"
    assert (
        saved_session.game_state["final_outcome"]["image_url"]
        == "https://example.com/final-board.png"
    )
    saved_ending_message = message_repo.create.call_args_list[-1].args[0]
    assert (
        saved_ending_message.parsed_response["final_outcome"]["image_url"]
        == "https://example.com/final-board.png"
    )
    assert (
        saved_ending_message.parsed_response["final_outcome"][
            "achievement_board"
        ]["ending_type"]
        == "defeat"
    )
    death_prompt = image_service.generate_image.call_args_list[-1].kwargs[
        "prompt"
    ]
    assert "This is a death scene, not a generic defeat scene." in death_prompt
    assert "collapsed, kneeling, fallen, or slumped posture" in death_prompt
    assert "cave mouth aftermath" not in death_prompt


@pytest.mark.asyncio
async def test_progression_death_narrative_uses_genre_specific_role():
    user_id = get_uuid7()
    scenario = _make_progression_scenario().model_copy(
        update={
            "name": "생존 기록",
            "world_setting": "감염체가 배회하는 폐허 도시에서 버틴다.",
            "genre": ScenarioGenre.SURVIVAL,
            "tags": ["생존", "아포칼립스"],
        }
    )
    character = _make_character(user_id, scenario.id)
    llm_service = AsyncMock()
    llm_response = MagicMock()
    llm_response.content = "하윤은 끝내 폐허 병원 바닥에 쓰러졌다."
    llm_service.generate_response.return_value = llm_response
    use_case = ProcessActionUseCase(
        session_repository=AsyncMock(),
        message_repository=AsyncMock(),
        character_repository=AsyncMock(),
        scenario_repository=AsyncMock(),
        llm_service=llm_service,
        cache_service=AsyncMock(),
        embedding_service=AsyncMock(),
    )

    await use_case._generate_progression_death_narrative(
        scenario=scenario,
        character=character,
        achievement_board={
            "title": "폐허생환자",
            "total_score": 12,
            "internal_power": 1,
            "external_power": 2,
            "manuals": [],
        },
        base_narrative="하윤은 쓰러졌다.",
    )

    death_prompt = llm_service.generate_response.await_args.kwargs[
        "system_prompt"
    ]
    assert "무협 성장형" not in death_prompt
    assert "성장형 텍스트 게임의 죽음 엔딩" in death_prompt


@pytest.mark.asyncio
async def test_progression_hp_zero_on_final_turn_takes_priority_over_score():
    user_id = get_uuid7()
    scenario = _make_progression_scenario()
    character = _make_character(user_id, scenario.id)
    now = datetime.now(timezone.utc)
    session = GameSessionEntity(
        id=get_uuid7(),
        user_id=user_id,
        character_id=character.id,
        scenario_id=scenario.id,
        current_location=scenario.initial_location,
        game_state={
            "hp": 6,
            "max_hp": 100,
            "internal_power": 70,
            "external_power": 55,
            "manuals": [
                {
                    "name": "비연신법",
                    "category": "movement",
                    "mastery": 30,
                    "aura": "azure",
                },
                {
                    "name": "현천진경",
                    "category": "internal",
                    "mastery": 15,
                    "aura": "neutral",
                },
            ],
        },
        status=SessionStatus.ACTIVE,
        turn_count=11,
        max_turns=12,
        started_at=now,
        last_activity_at=now,
    )

    session_repo = AsyncMock()
    session_repo.get_by_id.return_value = session
    session_repo.save.side_effect = lambda saved: saved
    message_repo = AsyncMock()
    character_repo = AsyncMock()
    character_repo.get_by_id.return_value = character
    scenario_repo = AsyncMock()
    scenario_repo.get_by_id.return_value = scenario
    llm_service = AsyncMock()
    cache_service = AsyncMock()
    cache_service.get.return_value = None
    embedding_service = AsyncMock()
    image_service = AsyncMock()
    image_service.generate_image.side_effect = [
        "https://example.com/month12.png",
        "https://example.com/final-board.png",
    ]

    llm_response = MagicMock()
    llm_response.content = """
```json
{
  "narrative": "마지막 힘을 짜내 절벽 끝까지 도달했지만, 전신의 상처가 동시에 터져 시야가 무너집니다.",
  "options": [],
  "consumes_turn": true,
  "image_focus": "절벽 끝에서 마지막 발을 내딛는 상처 입은 무인",
  "state_changes": {
    "hp_change": -10,
    "internal_power_delta": 1
  }
}
```
"""
    llm_response.usage.total_tokens = 80
    llm_service.generate_response.return_value = llm_response

    use_case = ProcessActionUseCase(
        session_repository=session_repo,
        message_repository=message_repo,
        character_repository=character_repo,
        scenario_repository=scenario_repo,
        llm_service=llm_service,
        cache_service=cache_service,
        embedding_service=embedding_service,
        image_service=image_service,
    )

    result = await use_case.execute(
        user_id,
        ProcessActionInput(
            session_id=session.id,
            action="마지막 한 달 동안 절벽을 오른다",
            idempotency_key="progression-final-turn-death-priority",
        ),
    )

    assert result.response.ending_type == "defeat"
    assert result.response.final_outcome.achievement_board.escaped is False
    assert (
        "탈출 실패" in result.response.final_outcome.achievement_board.summary
    )
    death_prompt = image_service.generate_image.call_args_list[-1].kwargs[
        "prompt"
    ]
    assert "This is a death scene, not a generic defeat scene." in death_prompt
    assert "collapsed, kneeling, fallen, or slumped posture" in death_prompt


@pytest.mark.asyncio
async def test_progression_final_turn_retries_when_options_are_not_empty():
    user_id = get_uuid7()
    scenario = _make_progression_scenario()
    character = _make_character(user_id, scenario.id)
    now = datetime.now(timezone.utc)
    session = GameSessionEntity(
        id=get_uuid7(),
        user_id=user_id,
        character_id=character.id,
        scenario_id=scenario.id,
        current_location=scenario.initial_location,
        game_state={
            "hp": 12,
            "max_hp": 100,
            "internal_power": 40,
            "external_power": 35,
            "manuals": [],
        },
        status=SessionStatus.ACTIVE,
        turn_count=11,
        max_turns=12,
        started_at=now,
        last_activity_at=now,
    )

    session_repo = AsyncMock()
    session_repo.get_by_id.return_value = session
    session_repo.save.side_effect = lambda saved: saved
    message_repo = AsyncMock()
    character_repo = AsyncMock()
    character_repo.get_by_id.return_value = character
    scenario_repo = AsyncMock()
    scenario_repo.get_by_id.return_value = scenario
    llm_service = AsyncMock()
    cache_service = AsyncMock()
    cache_service.get.return_value = None
    embedding_service = AsyncMock()
    image_service = AsyncMock()
    image_service.generate_image.side_effect = [
        "https://example.com/month12.png",
        "https://example.com/final-board.png",
    ]

    malformed_turn_response = MagicMock()
    malformed_turn_response.content = """
```json
{
  "narrative": "마지막 한 달 동안 출구를 향해 달려들었지만, 끝을 장담할 수는 없었다.",
  "options": [
    {"label": "빛을 향해 마지막 발을 내딛는다", "action_type": "progression"}
  ],
  "consumes_turn": true,
  "image_focus": "절벽 끝을 향해 달려드는 무인",
  "state_changes": {
    "hp_change": -3,
    "internal_power_delta": 1
  }
}
```
"""
    malformed_turn_response.usage.total_tokens = 60

    repaired_turn_response = MagicMock()
    repaired_turn_response.content = """
```json
{
  "narrative": "마지막 한 달 동안 출구를 향해 달려든 끝에, 하하는 모든 기력을 소진한 채 절벽 앞에 선다.",
  "options": [],
  "consumes_turn": true,
  "image_focus": "절벽 끝에서 마지막 기운을 끌어올리는 무인",
  "state_changes": {
    "hp_change": -3,
    "internal_power_delta": 1
  }
}
```
"""
    repaired_turn_response.usage.total_tokens = 62

    title_response = MagicMock()
    title_response.content = """
```json
{
  "title": "절벽수련객",
  "title_reason": "끝내 동굴의 마지막 문턱까지 도달한 수련자이기 때문입니다."
}
```
"""
    title_response.usage.total_tokens = 20

    ending_response = MagicMock()
    ending_response.content = (
        "하하는 마지막 문턱 앞에서 쓰러지며 동굴의 어둠 속에 남았다."
    )
    ending_response.usage.total_tokens = 30

    llm_service.generate_response.side_effect = [
        malformed_turn_response,
        repaired_turn_response,
        title_response,
        ending_response,
    ]

    use_case = ProcessActionUseCase(
        session_repository=session_repo,
        message_repository=message_repo,
        character_repository=character_repo,
        scenario_repository=scenario_repo,
        llm_service=llm_service,
        cache_service=cache_service,
        embedding_service=embedding_service,
        image_service=image_service,
    )

    result = await use_case.execute(
        user_id,
        ProcessActionInput(
            session_id=session.id,
            action="마지막 한 달 동안 출구를 향해 돌진한다",
            idempotency_key="progression-final-turn-option-retry",
        ),
    )

    assert llm_service.generate_response.await_count == 4
    assert result.response.ending_type == "defeat"
    saved_turn_message = message_repo.create.call_args_list[-2].args[0]
    assert saved_turn_message.parsed_response["options"] == []


@pytest.mark.asyncio
async def test_progression_final_turn_uses_dedicated_ending_narrative():
    user_id = get_uuid7()
    scenario = _make_progression_scenario()
    character = _make_character(user_id, scenario.id)
    now = datetime.now(timezone.utc)
    session = GameSessionEntity(
        id=get_uuid7(),
        user_id=user_id,
        character_id=character.id,
        scenario_id=scenario.id,
        current_location=scenario.initial_location,
        game_state={
            "hp": 30,
            "max_hp": 100,
            "internal_power": 22,
            "external_power": 20,
            "manuals": [
                {
                    "name": "비연신법",
                    "category": "movement",
                    "mastery": 30,
                    "aura": "azure",
                },
                {
                    "name": "현천진경",
                    "category": "internal",
                    "mastery": 15,
                    "aura": "neutral",
                },
                {
                    "name": "뇌정신장",
                    "category": "external",
                    "mastery": 15,
                    "aura": "violet",
                },
            ],
        },
        status=SessionStatus.ACTIVE,
        turn_count=11,
        max_turns=12,
        started_at=now,
        last_activity_at=now,
    )

    session_repo = AsyncMock()
    session_repo.get_by_id.return_value = session
    session_repo.save.side_effect = lambda saved: saved
    message_repo = AsyncMock()
    character_repo = AsyncMock()
    character_repo.get_by_id.return_value = character
    scenario_repo = AsyncMock()
    scenario_repo.get_by_id.return_value = scenario
    llm_service = AsyncMock()
    cache_service = AsyncMock()
    cache_service.get.return_value = None
    embedding_service = AsyncMock()
    image_service = AsyncMock()
    image_service.generate_image.side_effect = [
        "https://example.com/month12.png",
        "https://example.com/final-board.png",
    ]

    turn_response = MagicMock()
    turn_response.content = """
```json
{
  "narrative": "하하는 마지막 한 달, 모든 것을 걸고 절벽을 올라 마침내 탈출했습니다.",
  "options": [],
  "consumes_turn": true,
  "image_focus": "절벽 탈출구를 향해 몸을 던지는 지친 무인",
  "state_changes": {
    "hp_change": -5,
    "internal_power_delta": 0
  }
}
```
"""
    turn_response.usage.total_tokens = 90

    title_response = MagicMock()
    title_response.content = """
```json
{
  "title": "벽중수련객",
  "title_reason": "절벽 앞에서 끝내 쓰러졌지만 깊은 수련의 흔적을 남겼기 때문입니다."
}
```
"""
    title_response.usage.total_tokens = 20

    ending_response = MagicMock()
    ending_response.content = (
        "하하는 끝내 절벽 위에 닿지 못했고, 마지막 숨과 함께 "
        "동굴의 침묵 속으로 사라졌다."
    )
    ending_response.usage.total_tokens = 40
    llm_service.generate_response.side_effect = [
        turn_response,
        title_response,
        ending_response,
    ]

    use_case = ProcessActionUseCase(
        session_repository=session_repo,
        message_repository=message_repo,
        character_repository=character_repo,
        scenario_repository=scenario_repo,
        llm_service=llm_service,
        cache_service=cache_service,
        embedding_service=embedding_service,
        image_service=image_service,
    )

    result = await use_case.execute(
        user_id,
        ProcessActionInput(
            session_id=session.id,
            action="마지막 한 달 동안 청광심법을 연마한다",
            idempotency_key="progression-final-ending-narrative",
        ),
    )

    assert result.response.ending_type == "defeat"
    assert "탈출했습니다" not in result.response.final_outcome.narrative
    assert (
        result.response.final_outcome.narrative
        == "하하는 끝내 절벽 위에 닿지 못했고, 마지막 숨과 함께 동굴의 침묵 속으로 사라졌다."
    )
    assert (
        "탈출 실패" in result.response.final_outcome.achievement_board.summary
    )


@pytest.mark.asyncio
async def test_progression_generates_and_persists_final_title():
    user_id = get_uuid7()
    scenario = _make_progression_scenario()
    character = _make_character(user_id, scenario.id)
    now = datetime.now(timezone.utc)
    session = GameSessionEntity(
        id=get_uuid7(),
        user_id=user_id,
        character_id=character.id,
        scenario_id=scenario.id,
        current_location=scenario.initial_location,
        game_state={
            "hp": 34,
            "max_hp": 100,
            "internal_power": 45,
            "external_power": 38,
            "manuals": [
                {
                    "name": "청광심법",
                    "category": "internal",
                    "mastery": 28,
                    "aura": "azure",
                }
            ],
            "traits": ["청광의 숨결"],
            "title_candidates": ["청광수련객"],
        },
        status=SessionStatus.ACTIVE,
        turn_count=11,
        max_turns=12,
        started_at=now,
        last_activity_at=now,
    )

    session_repo = AsyncMock()
    session_repo.get_by_id.return_value = session
    session_repo.save.side_effect = lambda saved: saved
    message_repo = AsyncMock()
    character_repo = AsyncMock()
    character_repo.get_by_id.return_value = character
    scenario_repo = AsyncMock()
    scenario_repo.get_by_id.return_value = scenario
    llm_service = AsyncMock()
    cache_service = AsyncMock()
    cache_service.get.return_value = None
    embedding_service = AsyncMock()
    image_service = AsyncMock()
    image_service.generate_image.side_effect = [
        "https://example.com/month12.png",
        "https://example.com/final-board.png",
    ]

    turn_response = MagicMock()
    turn_response.content = """
```json
{
  "narrative": "하하는 마지막 수련을 끝내고 동굴 입구의 찬 기운과 마주했다.",
  "options": [],
  "consumes_turn": true,
  "image_focus": "동굴 입구의 냉기를 마주한 채 숨을 고르는 무인",
  "state_changes": {
    "hp_change": -4,
    "internal_power_delta": 2
  }
}
```
"""
    turn_response.usage.total_tokens = 80

    title_response = MagicMock()
    title_response.content = """
```json
{
  "title": "청광동천객",
  "title_reason": "청광심법과 깊어진 내공으로 동굴의 끝에 닿은 수련자이기 때문입니다."
}
```
"""
    title_response.usage.total_tokens = 30

    ending_response = MagicMock()
    ending_response.content = (
        "하하는 마침내 동굴의 끝에서 새로운 이름을 얻었다."
    )
    ending_response.usage.total_tokens = 25

    llm_service.generate_response.side_effect = [
        turn_response,
        title_response,
        ending_response,
    ]

    use_case = ProcessActionUseCase(
        session_repository=session_repo,
        message_repository=message_repo,
        character_repository=character_repo,
        scenario_repository=scenario_repo,
        llm_service=llm_service,
        cache_service=cache_service,
        embedding_service=embedding_service,
        image_service=image_service,
    )

    result = await use_case.execute(
        user_id,
        ProcessActionInput(
            session_id=session.id,
            action="마지막 한 달 동안 청광심법을 갈고닦는다",
            idempotency_key="progression-final-title-persist",
        ),
    )

    assert (
        result.response.final_outcome.achievement_board.title == "청광동천객"
    )
    assert (
        result.response.final_outcome.achievement_board.title_reason
        == "청광심법과 깊어진 내공으로 동굴의 끝에 닿은 수련자이기 때문입니다."
    )
    saved_session = session_repo.save.call_args.args[0]
    assert (
        saved_session.game_state["final_outcome"]["achievement_board"]["title"]
        == "청광동천객"
    )
    assert (
        saved_session.game_state["final_outcome"]["achievement_board"][
            "title_reason"
        ]
        == "청광심법과 깊어진 내공으로 동굴의 끝에 닿은 수련자이기 때문입니다."
    )


@pytest.mark.asyncio
async def test_progression_uses_default_title_when_generated_title_is_invalid():
    user_id = get_uuid7()
    scenario = _make_progression_scenario()
    character = _make_character(user_id, scenario.id)
    now = datetime.now(timezone.utc)
    session = GameSessionEntity(
        id=get_uuid7(),
        user_id=user_id,
        character_id=character.id,
        scenario_id=scenario.id,
        current_location=scenario.initial_location,
        game_state={
            "hp": 5,
            "max_hp": 100,
            "internal_power": 50,
            "external_power": 30,
            "manuals": [],
            "traits": ["절벽의 상흔"],
            "title_candidates": ["절벽생환자"],
        },
        status=SessionStatus.ACTIVE,
        turn_count=11,
        max_turns=12,
        started_at=now,
        last_activity_at=now,
    )

    session_repo = AsyncMock()
    session_repo.get_by_id.return_value = session
    session_repo.save.side_effect = lambda saved: saved
    message_repo = AsyncMock()
    character_repo = AsyncMock()
    character_repo.get_by_id.return_value = character
    scenario_repo = AsyncMock()
    scenario_repo.get_by_id.return_value = scenario
    llm_service = AsyncMock()
    cache_service = AsyncMock()
    cache_service.get.return_value = None
    embedding_service = AsyncMock()
    image_service = AsyncMock()
    image_service.generate_image.side_effect = [
        "https://example.com/month12.png",
        "https://example.com/final-board.png",
    ]

    turn_response = MagicMock()
    turn_response.content = """
```json
{
  "narrative": "하하는 마지막 힘을 짜내지만, 동굴의 벽은 더 이상 길을 열어주지 않았다.",
  "options": [],
  "consumes_turn": true,
  "image_focus": "막힌 동굴 벽 앞에서 마지막 힘을 끌어모으는 무인",
  "state_changes": {
    "hp_change": -2,
    "internal_power_delta": 0
  }
}
```
"""
    turn_response.usage.total_tokens = 80

    title_response = MagicMock()
    title_response.content = """
```json
{
  "title": "동굴파천객",
  "title_reason": "패배했지만 사실상 탈출과 다름없는 경지였기 때문입니다."
}
```
"""
    title_response.usage.total_tokens = 30

    ending_response = MagicMock()
    ending_response.content = (
        "하하는 끝내 동굴을 넘지 못하고 다시 침묵 속에 남았다."
    )
    ending_response.usage.total_tokens = 25

    llm_service.generate_response.side_effect = [
        turn_response,
        title_response,
        ending_response,
    ]

    use_case = ProcessActionUseCase(
        session_repository=session_repo,
        message_repository=message_repo,
        character_repository=character_repo,
        scenario_repository=scenario_repo,
        llm_service=llm_service,
        cache_service=cache_service,
        embedding_service=embedding_service,
        image_service=image_service,
    )

    result = await use_case.execute(
        user_id,
        ProcessActionInput(
            session_id=session.id,
            action="마지막 한 달 동안 탈출을 시도한다",
            idempotency_key="progression-final-title-default",
        ),
    )

    assert result.response.final_outcome.achievement_board.escaped is False
    assert (
        result.response.final_outcome.achievement_board.title != "동굴파천객"
    )
    assert (
        result.response.final_outcome.achievement_board.title == "동굴생환자"
    )
