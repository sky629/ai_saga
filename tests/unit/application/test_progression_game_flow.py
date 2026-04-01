"""Progression 게임 타입 흐름 단위 테스트."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

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
        genre=ScenarioGenre.HISTORICAL,
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
    assert saved_session.game_state["internal_power"] == 5
    assert saved_session.game_state["external_power"] == 10
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
    assert result.response.status_panel["remaining_turns"] == 12
    saved_session = session_repo.save.call_args.args[0]
    assert saved_session.turn_count == 0


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
    assert result.response.status_panel["internal_power"] == 7
    assert result.response.status_panel["external_power"] == 14
    assert result.response.status_panel["remaining_turns"] == 11

    saved_session = session_repo.save.call_args.args[0]
    assert saved_session.turn_count == 1
    assert saved_session.game_state["hp"] == 92
    assert saved_session.game_state["manuals"][0]["name"] == "천잠신공"


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
            idempotency_key="progression-manual-fallback",
        ),
    )

    assert (
        result.response.status_panel["manuals"][0]["name"]
        == "청룡심법(靑龍心法)"
    )
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

    assert result.response.status_panel["manuals"][0]["mastery"] == 10
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
            idempotency_key="progression-zero-mastery-fallback",
        ),
    )

    assert result.response.status_panel["manuals"][0]["mastery"] == 10
    created_message = message_repo.create.call_args_list[-1].args[0]
    assert (
        created_message.parsed_response["state_changes"][
            "manual_mastery_updates"
        ][0]["mastery_delta"]
        == 5
    )
