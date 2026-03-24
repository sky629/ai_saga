"""Unit tests for dice system integration in ProcessActionUseCase."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from app.game.application.use_cases.process_action import (
    ProcessActionInput,
    ProcessActionUseCase,
)
from app.game.domain.entities import CharacterEntity, CharacterStats
from app.game.domain.value_objects import (
    ActionType,
    ScenarioDifficulty,
    SessionStatus,
)
from app.game.domain.value_objects.dice import DiceCheckType, DiceResult


@pytest.mark.parametrize(
    ("action", "expected"),
    [
        ("적을 공격한다", ActionType.COMBAT),
        ("상인을 설득한다", ActionType.SOCIAL),
        ("자물쇠를 해제한다", ActionType.SKILL),
        ("북쪽으로 이동한다", ActionType.MOVEMENT),
        ("칼을 뽑는다", ActionType.OBSERVATION),
        ("칼을 뽑고 탈출한다", ActionType.EXPLORATION),
        ("무기를 꺼내 문을 연다", ActionType.EXPLORATION),
        (
            "칼을 든 채 경비병들을 노려본다. 그러다가 경비병이 한 눈 판 사이에 칼을 휘두른다",
            ActionType.COMBAT,
        ),
    ],
)
def test_resolve_action_type(action, expected):
    assert ProcessActionUseCase._resolve_action_type(action) == expected


@pytest.fixture
def mock_repositories():
    mock_session_repository = AsyncMock()
    mock_message_repository = AsyncMock()
    mock_character_repository = AsyncMock()
    mock_scenario_repository = AsyncMock()
    mock_llm_service = AsyncMock()
    mock_cache_service = AsyncMock()
    mock_embedding_service = AsyncMock()

    return {
        "session_repository": mock_session_repository,
        "message_repository": mock_message_repository,
        "character_repository": mock_character_repository,
        "scenario_repository": mock_scenario_repository,
        "llm_service": mock_llm_service,
        "cache_service": mock_cache_service,
        "embedding_service": mock_embedding_service,
    }


@pytest.fixture
def active_session():
    """Create an active session fixture."""
    from datetime import datetime

    from app.game.domain.entities import GameSessionEntity

    now = datetime.now()
    return GameSessionEntity(
        id=UUID("12345678-1234-1234-1234-123456789abc"),
        character_id=UUID("abcdef12-1234-1234-1234-123456789abc"),
        scenario_id=UUID("87654321-4321-4321-4321-cba987654321"),
        user_id=UUID("11111111-1111-1111-1111-111111111111"),
        current_location="Test Location",
        game_state={},
        status=SessionStatus.ACTIVE,
        turn_count=1,
        max_turns=10,
        is_active=True,
        started_at=now,
        last_activity_at=now,
    )


@pytest.fixture
def character():
    """Create a character fixture."""
    from datetime import datetime

    return CharacterEntity(
        id=UUID("abcdef12-1234-1234-1234-123456789abc"),
        user_id=UUID("11111111-1111-1111-1111-111111111111"),
        scenario_id=UUID("87654321-4321-4321-4321-cba987654321"),
        name="Test Character",
        description="A test character",
        stats=CharacterStats(hp=100, max_hp=100, level=5),
        inventory=[],
        is_active=True,
        created_at=datetime.now(),
    )


@pytest.fixture
def scenario():
    """Create a scenario fixture."""
    from datetime import datetime

    from app.game.domain.entities import ScenarioEntity

    return ScenarioEntity(
        id=UUID("87654321-4321-4321-4321-cba987654321"),
        name="Test Scenario",
        description="A test scenario",
        genre="fantasy",
        difficulty=ScenarioDifficulty.NORMAL,
        max_turns=10,
        world_setting="A fantasy world",
        initial_location="Starting Town",
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


class TestDiceIntegration:
    """Test dice system integration in ProcessActionUseCase."""

    @pytest.mark.asyncio
    async def test_dice_result_in_response(
        self, mock_repositories, active_session, character, scenario
    ):
        """Test that dice_result is included in GameActionResponse."""
        # Setup
        mock_repositories["cache_service"].get.return_value = None
        mock_repositories["session_repository"].get_by_id.return_value = (
            active_session
        )
        mock_repositories["character_repository"].get_by_id.return_value = (
            character
        )
        mock_repositories["scenario_repository"].get_by_id.return_value = (
            scenario
        )
        mock_repositories[
            "embedding_service"
        ].generate_embedding.return_value = [0.1, 0.2, 0.3]

        # Mock LLM response
        mock_llm_response = MagicMock()
        mock_llm_response.content = '{"narrative": "Fumble!", "options": ["Option 1"], "dice_applied": true, "state_changes": {"hp_change": 0}}'
        mock_llm_response.usage.total_tokens = 100
        mock_repositories["llm_service"].generate_response.return_value = (
            mock_llm_response
        )

        # Mock dice roll
        with patch(
            "app.game.domain.services.dice_service.random.randint"
        ) as mock_randint:
            mock_randint.return_value = 15

            use_case = ProcessActionUseCase(**mock_repositories)
            input_data = ProcessActionInput(
                session_id=active_session.id,
                action="attack",
                idempotency_key="test-key",
            )

            result = await use_case.execute(active_session.user_id, input_data)

        # Verify dice_result in response
        assert result.response.dice_result is not None
        assert result.response.dice_result.roll == 15
        assert result.response.dice_result.modifier == 3  # Level 5 = +3
        assert result.response.dice_result.dc == 13  # NORMAL difficulty
        assert result.response.dice_result.is_success is True
        assert result.response.dice_result.check_type == "combat"
        assert result.response.options[0].label == "Option 1"
        assert result.response.options[0].action_type == "exploration"
        assert result.response.options[0].requires_dice is True

    @pytest.mark.asyncio
    async def test_critical_hit(
        self, mock_repositories, active_session, character, scenario
    ):
        """Test critical hit (roll=20) includes damage."""
        mock_repositories["cache_service"].get.return_value = None
        mock_repositories["session_repository"].get_by_id.return_value = (
            active_session
        )
        mock_repositories["character_repository"].get_by_id.return_value = (
            character
        )
        mock_repositories["scenario_repository"].get_by_id.return_value = (
            scenario
        )
        mock_repositories[
            "embedding_service"
        ].generate_embedding.return_value = [0.1, 0.2, 0.3]

        mock_llm_response = MagicMock()
        mock_llm_response.content = '{"narrative": "Critical!", "options": ["Option 1"], "dice_applied": true, "state_changes": {"hp_change": 0}}'
        mock_llm_response.usage.total_tokens = 100
        mock_repositories["llm_service"].generate_response.return_value = (
            mock_llm_response
        )

        with patch(
            "app.game.domain.services.dice_service.random.randint"
        ) as mock_randint:
            mock_randint.side_effect = [20, 5, 3]  # Roll 20, then damage dice

            use_case = ProcessActionUseCase(**mock_repositories)
            input_data = ProcessActionInput(
                session_id=active_session.id,
                action="attack",
                idempotency_key="test-key",
            )

            result = await use_case.execute(active_session.user_id, input_data)

        assert result.response.dice_result.is_critical is True
        assert result.response.dice_result.damage is not None
        assert result.response.dice_result.damage > 0

    @pytest.mark.asyncio
    async def test_server_overrides_llm_hp_change_without_dice_applied_flag(
        self, mock_repositories, active_session, character, scenario
    ):
        mock_repositories["cache_service"].get.return_value = None
        mock_repositories["session_repository"].get_by_id.return_value = (
            active_session
        )
        mock_repositories["character_repository"].get_by_id.return_value = (
            character
        )
        mock_repositories["scenario_repository"].get_by_id.return_value = (
            scenario
        )
        mock_repositories[
            "embedding_service"
        ].generate_embedding.return_value = [0.1, 0.2, 0.3]

        mock_llm_response = MagicMock()
        mock_llm_response.content = '{"narrative": "Success!", "options": ["Option 1"], "dice_applied": false, "state_changes": {"hp_change": -50}}'
        mock_llm_response.usage.total_tokens = 100
        mock_repositories["llm_service"].generate_response.return_value = (
            mock_llm_response
        )

        with patch(
            "app.game.domain.services.dice_service.random.randint"
        ) as mock_randint:
            mock_randint.return_value = 15

            use_case = ProcessActionUseCase(**mock_repositories)
            input_data = ProcessActionInput(
                session_id=active_session.id,
                action="attack",
                idempotency_key="test-key",
            )

            result = await use_case.execute(active_session.user_id, input_data)

        assert result.response.dice_result is None
        mock_repositories["character_repository"].save.assert_not_called()

    @pytest.mark.asyncio
    async def test_server_ignores_llm_dice_flag_for_simple_movement(
        self, mock_repositories, active_session, character, scenario
    ):
        mock_repositories["cache_service"].get.return_value = None
        mock_repositories["session_repository"].get_by_id.return_value = (
            active_session
        )
        mock_repositories["character_repository"].get_by_id.return_value = (
            character
        )
        mock_repositories["scenario_repository"].get_by_id.return_value = (
            scenario
        )
        mock_repositories[
            "embedding_service"
        ].generate_embedding.return_value = [0.1, 0.2, 0.3]

        mock_llm_response = MagicMock()
        mock_llm_response.content = (
            '{"before_narrative": "당신은 북쪽 통로로 발을 옮깁니다.", '
            '"narrative": "당신은 북쪽 통로로 이동합니다.", '
            '"options": ["주변을 살핀다"], '
            '"dice_applied": true, '
            '"state_changes": {"location": "북쪽 통로"}}'
        )
        mock_llm_response.usage.total_tokens = 100
        mock_repositories["llm_service"].generate_response.return_value = (
            mock_llm_response
        )

        with patch(
            "app.game.domain.services.dice_service.random.randint"
        ) as mock_randint:
            use_case = ProcessActionUseCase(**mock_repositories)
            input_data = ProcessActionInput(
                session_id=active_session.id,
                action="북쪽으로 이동한다",
                idempotency_key="move-no-dice-key",
            )

            result = await use_case.execute(active_session.user_id, input_data)

        assert result.response.dice_result is None
        assert result.response.before_roll_narrative is None
        mock_randint.assert_not_called()

    @pytest.mark.asyncio
    async def test_weapon_draw_preparation_does_not_trigger_dice(
        self, mock_repositories, active_session, character, scenario
    ):
        mock_repositories["cache_service"].get.return_value = None
        mock_repositories["session_repository"].get_by_id.return_value = (
            active_session
        )
        mock_repositories["character_repository"].get_by_id.return_value = (
            character
        )
        mock_repositories["scenario_repository"].get_by_id.return_value = (
            scenario
        )
        mock_repositories[
            "embedding_service"
        ].generate_embedding.return_value = [0.1, 0.2, 0.3]

        mock_llm_response = MagicMock()
        mock_llm_response.content = (
            '{"before_narrative": "당신은 칼자루에 손을 얹습니다.", '
            '"narrative": "당신은 천천히 칼을 뽑아 듭니다.", '
            '"options": ["주변을 살핀다"], '
            '"dice_applied": true, '
            '"state_changes": {"hp_change": 0}}'
        )
        mock_llm_response.usage.total_tokens = 100
        mock_repositories["llm_service"].generate_response.return_value = (
            mock_llm_response
        )

        with patch(
            "app.game.domain.services.dice_service.random.randint"
        ) as mock_randint:
            use_case = ProcessActionUseCase(**mock_repositories)
            input_data = ProcessActionInput(
                session_id=active_session.id,
                action="칼을 뽑는다",
                idempotency_key="weapon-draw-no-dice-key",
            )

            result = await use_case.execute(active_session.user_id, input_data)

        assert result.response.dice_result is None
        assert result.response.before_roll_narrative is None
        mock_randint.assert_not_called()

    @pytest.mark.asyncio
    async def test_client_action_type_hint_cannot_bypass_combat_dice(
        self, mock_repositories, active_session, character, scenario
    ):
        mock_repositories["cache_service"].get.return_value = None
        mock_repositories["session_repository"].get_by_id.return_value = (
            active_session
        )
        mock_repositories["character_repository"].get_by_id.return_value = (
            character
        )
        mock_repositories["scenario_repository"].get_by_id.return_value = (
            scenario
        )
        mock_repositories[
            "embedding_service"
        ].generate_embedding.return_value = [0.1, 0.2, 0.3]

        mock_llm_response = MagicMock()
        mock_llm_response.content = (
            '{"before_narrative": "당신은 검을 들어올립니다.", '
            '"narrative": "검격이 적중합니다.", '
            '"options": ["계속 공격한다"], '
            '"dice_applied": true, '
            '"state_changes": {"hp_change": 0}}'
        )
        mock_llm_response.usage.total_tokens = 100
        mock_repositories["llm_service"].generate_response.return_value = (
            mock_llm_response
        )

        with patch(
            "app.game.domain.services.dice_service.random.randint"
        ) as mock_randint:
            mock_randint.return_value = 15

            use_case = ProcessActionUseCase(**mock_repositories)
            input_data = ProcessActionInput(
                session_id=active_session.id,
                action="고블린을 공격한다",
                action_type="movement",
                idempotency_key="combat-hint-bypass-key",
            )

            result = await use_case.execute(active_session.user_id, input_data)

        assert result.response.dice_result is not None
        assert result.response.dice_result.check_type == "combat"
        mock_randint.assert_called()

    @pytest.mark.asyncio
    async def test_unclassified_free_form_action_falls_back_to_dice_check(
        self, mock_repositories, active_session, character, scenario
    ):
        mock_repositories["cache_service"].get.return_value = None
        mock_repositories["session_repository"].get_by_id.return_value = (
            active_session
        )
        mock_repositories["character_repository"].get_by_id.return_value = (
            character
        )
        mock_repositories["scenario_repository"].get_by_id.return_value = (
            scenario
        )
        mock_repositories[
            "embedding_service"
        ].generate_embedding.return_value = [0.1, 0.2, 0.3]

        mock_llm_response = MagicMock()
        mock_llm_response.content = (
            '{"before_narrative": "당신은 무거운 석상을 밀어봅니다.", '
            '"narrative": "석상이 삐걱이며 움직입니다.", '
            '"options": ["안쪽을 확인한다"], '
            '"dice_applied": true, '
            '"state_changes": {"discoveries": ["숨겨진 통로"]}}'
        )
        mock_llm_response.usage.total_tokens = 100
        mock_repositories["llm_service"].generate_response.return_value = (
            mock_llm_response
        )

        with patch(
            "app.game.domain.services.dice_service.random.randint"
        ) as mock_randint:
            mock_randint.return_value = 14

            use_case = ProcessActionUseCase(**mock_repositories)
            input_data = ProcessActionInput(
                session_id=active_session.id,
                action="석상을 밀어 숨겨진 통로가 있는지 본다",
                idempotency_key="free-form-dice-key",
            )

            result = await use_case.execute(active_session.user_id, input_data)

        assert result.response.dice_result is not None
        assert result.response.dice_result.check_type == "exploration"
        mock_randint.assert_called()

    @pytest.mark.asyncio
    async def test_failed_dice_narrative_preserves_llm_description(
        self, mock_repositories, active_session, character, scenario
    ):
        mock_repositories["cache_service"].get.return_value = None
        mock_repositories["session_repository"].get_by_id.return_value = (
            active_session
        )
        mock_repositories["character_repository"].get_by_id.return_value = (
            character
        )
        mock_repositories["scenario_repository"].get_by_id.return_value = (
            scenario
        )
        mock_repositories[
            "embedding_service"
        ].generate_embedding.return_value = [0.1, 0.2, 0.3]

        mock_llm_response = MagicMock()
        mock_llm_response.content = (
            '{"before_narrative": "당신은 칼자루를 움켜쥡니다.", '
            '"narrative": "당신은 칼을 뽑아 전투 태세를 갖춥니다.", '
            '"options": ["다시 시도한다"], '
            '"dice_applied": true, '
            '"state_changes": {"hp_change": 0}}'
        )
        mock_llm_response.usage.total_tokens = 100
        mock_repositories["llm_service"].generate_response.return_value = (
            mock_llm_response
        )

        with patch(
            "app.game.domain.services.dice_service.random.randint"
        ) as mock_randint:
            mock_randint.return_value = 2

            use_case = ProcessActionUseCase(**mock_repositories)
            input_data = ProcessActionInput(
                session_id=active_session.id,
                action="적에게 칼을 휘두른다",
                idempotency_key="failed-narrative-sanitize-key",
            )

            result = await use_case.execute(active_session.user_id, input_data)

        assert result.response.dice_result is not None
        assert result.response.dice_result.is_success is False
        assert "칼을 뽑아 전투 태세를 갖춥니다." in result.response.narrative

    @pytest.mark.asyncio
    async def test_persisted_parsed_response_keeps_raw_llm_option_schema(
        self, mock_repositories, active_session, character, scenario
    ):
        mock_repositories["cache_service"].get.return_value = None
        mock_repositories["session_repository"].get_by_id.return_value = (
            active_session
        )
        mock_repositories["character_repository"].get_by_id.return_value = (
            character
        )
        mock_repositories["scenario_repository"].get_by_id.return_value = (
            scenario
        )
        mock_repositories[
            "embedding_service"
        ].generate_embedding.return_value = [0.1, 0.2, 0.3]

        mock_llm_response = MagicMock()
        mock_llm_response.content = (
            '{"narrative": "테스트", '
            '"options": ["Option 1", "Option 2"], '
            '"dice_applied": false, '
            '"state_changes": {"hp_change": 0}}'
        )
        mock_llm_response.usage.total_tokens = 100
        mock_repositories["llm_service"].generate_response.return_value = (
            mock_llm_response
        )

        with patch(
            "app.game.domain.services.dice_service.random.randint"
        ) as mock_randint:
            mock_randint.return_value = 15

            use_case = ProcessActionUseCase(**mock_repositories)
            input_data = ProcessActionInput(
                session_id=active_session.id,
                action="attack",
                idempotency_key="parsed-response-schema-key",
            )

            await use_case.execute(active_session.user_id, input_data)

        saved_ai_message = (
            mock_repositories["message_repository"]
            .create.await_args_list[-1]
            .args[0]
        )
        assert saved_ai_message.parsed_response["options"] == [
            "Option 1",
            "Option 2",
        ]

    @pytest.mark.asyncio
    async def test_persisted_parsed_response_keeps_failed_dice_hp_change_when_applied(
        self, mock_repositories, active_session, character, scenario
    ):
        mock_repositories["cache_service"].get.return_value = None
        mock_repositories["session_repository"].get_by_id.return_value = (
            active_session
        )
        mock_repositories["character_repository"].get_by_id.return_value = (
            character
        )
        mock_repositories["scenario_repository"].get_by_id.return_value = (
            scenario
        )
        mock_repositories[
            "embedding_service"
        ].generate_embedding.return_value = [0.1, 0.2, 0.3]

        mock_llm_response = MagicMock()
        mock_llm_response.content = (
            '{"narrative": "실패했지만 큰 상처를 입습니다.", '
            '"options": ["Option 1"], '
            '"dice_applied": true, '
            '"state_changes": {"hp_change": -5}}'
        )
        mock_llm_response.usage.total_tokens = 100
        mock_repositories["llm_service"].generate_response.return_value = (
            mock_llm_response
        )

        with patch(
            "app.game.domain.services.dice_service.random.randint"
        ) as mock_randint:
            mock_randint.return_value = 9

            use_case = ProcessActionUseCase(**mock_repositories)
            input_data = ProcessActionInput(
                session_id=active_session.id,
                action="문을 힘으로 연다",
                idempotency_key="sanitized-hp-failed-dice-key",
            )

            await use_case.execute(active_session.user_id, input_data)

        saved_ai_message = (
            mock_repositories["message_repository"]
            .create.await_args_list[-1]
            .args[0]
        )
        assert (
            saved_ai_message.parsed_response["state_changes"]["hp_change"]
            == -5
        )

    @pytest.mark.asyncio
    async def test_persisted_parsed_response_uses_fumble_damage_for_hp_change(
        self, mock_repositories, active_session, character, scenario
    ):
        mock_repositories["cache_service"].get.return_value = None
        mock_repositories["session_repository"].get_by_id.return_value = (
            active_session
        )
        mock_repositories["character_repository"].get_by_id.return_value = (
            character
        )
        mock_repositories["scenario_repository"].get_by_id.return_value = (
            scenario
        )
        mock_repositories[
            "embedding_service"
        ].generate_embedding.return_value = [0.1, 0.2, 0.3]

        mock_llm_response = MagicMock()
        mock_llm_response.content = (
            '{"narrative": "대실패!", '
            '"options": ["Option 1"], '
            '"dice_applied": true, '
            '"state_changes": {"hp_change": 0}}'
        )
        mock_llm_response.usage.total_tokens = 100
        mock_repositories["llm_service"].generate_response.return_value = (
            mock_llm_response
        )

        with patch(
            "app.game.domain.services.dice_service.random.randint"
        ) as mock_randint:
            mock_randint.side_effect = [1, 2]

            use_case = ProcessActionUseCase(**mock_repositories)
            input_data = ProcessActionInput(
                session_id=active_session.id,
                action="적에게 돌진한다",
                idempotency_key="sanitized-hp-fumble-key",
            )

            await use_case.execute(active_session.user_id, input_data)

        saved_ai_message = (
            mock_repositories["message_repository"]
            .create.await_args_list[-1]
            .args[0]
        )
        assert (
            saved_ai_message.parsed_response["state_changes"]["hp_change"]
            == -2
        )

    @pytest.mark.asyncio
    async def test_fumble_self_damage(
        self, mock_repositories, active_session, character, scenario
    ):
        """Test fumble (roll=1) applies self-damage."""
        mock_repositories["cache_service"].get.return_value = None
        mock_repositories["session_repository"].get_by_id.return_value = (
            active_session
        )
        mock_repositories["character_repository"].get_by_id.return_value = (
            character
        )
        mock_repositories["scenario_repository"].get_by_id.return_value = (
            scenario
        )
        mock_repositories[
            "embedding_service"
        ].generate_embedding.return_value = [0.1, 0.2, 0.3]

        mock_llm_response = MagicMock()
        mock_llm_response.content = '{"narrative": "Fumble!", "options": ["Option 1"], "dice_applied": true, "state_changes": {"hp_change": 0}}'
        mock_llm_response.usage.total_tokens = 100
        mock_repositories["llm_service"].generate_response.return_value = (
            mock_llm_response
        )

        # Track character updates
        updated_hp = None

        async def save_character(char):
            nonlocal updated_hp
            updated_hp = char.stats.hp
            return char

        mock_repositories["character_repository"].save.side_effect = (
            save_character
        )

        with patch(
            "app.game.domain.services.dice_service.random.randint"
        ) as mock_randint:
            mock_randint.return_value = 1  # Fumble!

            use_case = ProcessActionUseCase(**mock_repositories)
            input_data = ProcessActionInput(
                session_id=active_session.id,
                action="attack",
                idempotency_key="test-key",
            )

            result = await use_case.execute(active_session.user_id, input_data)

        assert result.response.dice_result.is_fumble is True
        assert result.response.dice_result.damage is not None
        # HP should be reduced by fumble damage (1d4)
        assert updated_hp < character.stats.hp

    @pytest.mark.asyncio
    async def test_fumble_self_damage_applies_when_dice_not_applied(
        self, mock_repositories, active_session, character, scenario
    ):
        low_hp_character = CharacterEntity(
            id=character.id,
            user_id=character.user_id,
            scenario_id=character.scenario_id,
            name=character.name,
            profile=character.profile,
            stats=CharacterStats(hp=10, max_hp=100, level=5),
            inventory=character.inventory,
            is_active=True,
            created_at=character.created_at,
        )

        mock_repositories["cache_service"].get.return_value = None
        mock_repositories["session_repository"].get_by_id.return_value = (
            active_session
        )

        current_character = low_hp_character

        async def get_character_by_id(char_id):
            return current_character

        async def save_character(saved_character):
            nonlocal current_character
            current_character = saved_character
            return saved_character

        mock_repositories["character_repository"].get_by_id.side_effect = (
            get_character_by_id
        )
        mock_repositories["character_repository"].save.side_effect = (
            save_character
        )
        mock_repositories["scenario_repository"].get_by_id.return_value = (
            scenario
        )
        mock_repositories[
            "embedding_service"
        ].generate_embedding.return_value = [0.1, 0.2, 0.3]

        mock_llm_response = MagicMock()
        mock_llm_response.content = '{"narrative": "Fumble!", "options": ["Option 1"], "dice_applied": false, "state_changes": {"hp_change": 0}}'
        mock_llm_response.usage.total_tokens = 100
        mock_repositories["llm_service"].generate_response.return_value = (
            mock_llm_response
        )

        with patch(
            "app.game.domain.services.dice_service.random.randint"
        ) as mock_randint:
            mock_randint.side_effect = [1, 2]

            use_case = ProcessActionUseCase(**mock_repositories)
            input_data = ProcessActionInput(
                session_id=active_session.id,
                action="attack",
                idempotency_key="test-key",
            )

            result = await use_case.execute(active_session.user_id, input_data)

        assert result.response.dice_result is None
        assert current_character.stats.hp == 8

    @pytest.mark.asyncio
    async def test_hp_zero_death(
        self, mock_repositories, active_session, character, scenario
    ):
        low_hp_character = CharacterEntity(
            id=character.id,
            user_id=character.user_id,
            scenario_id=character.scenario_id,
            name=character.name,
            profile=character.profile,
            stats=CharacterStats(hp=1, max_hp=100, level=5),
            inventory=character.inventory,
            is_active=True,
            created_at=character.created_at,
        )

        mock_repositories["cache_service"].get.return_value = None
        mock_repositories["session_repository"].get_by_id.return_value = (
            active_session
        )

        # Track character state across multiple get_by_id calls
        current_character = low_hp_character

        async def get_character_by_id(char_id):
            return current_character

        async def save_character(char):
            nonlocal current_character
            current_character = char
            return char

        mock_repositories["character_repository"].get_by_id.side_effect = (
            get_character_by_id
        )
        mock_repositories["character_repository"].save.side_effect = (
            save_character
        )
        mock_repositories["scenario_repository"].get_by_id.return_value = (
            scenario
        )
        mock_repositories[
            "embedding_service"
        ].generate_embedding.return_value = [0.1, 0.2, 0.3]

        mock_llm_response = MagicMock()
        mock_llm_response.content = '{"narrative": "Fumble!", "options": ["Option 1"], "dice_applied": true, "state_changes": {"hp_change": 0}}'
        mock_llm_response.usage.total_tokens = 100
        mock_repositories["llm_service"].generate_response.return_value = (
            mock_llm_response
        )

        with patch(
            "app.game.domain.services.dice_service.random.randint"
        ) as mock_randint:
            mock_randint.return_value = 1  # Fumble with 1d4 damage

            use_case = ProcessActionUseCase(**mock_repositories)
            input_data = ProcessActionInput(
                session_id=active_session.id,
                action="attack",
                idempotency_key="test-key",
            )

            result = await use_case.execute(active_session.user_id, input_data)

        # Should return death ending
        assert result.response.is_ending is True
        assert (
            "사망" in result.response.narrative
            or "death" in result.response.narrative.lower()
        )

    @pytest.mark.asyncio
    async def test_dice_result_in_prompt(
        self, mock_repositories, active_session, character, scenario
    ):
        """Test dice result is passed to LLM prompt."""
        mock_repositories["cache_service"].get.return_value = None
        mock_repositories["session_repository"].get_by_id.return_value = (
            active_session
        )
        mock_repositories["character_repository"].get_by_id.return_value = (
            character
        )
        mock_repositories["scenario_repository"].get_by_id.return_value = (
            scenario
        )
        mock_repositories[
            "embedding_service"
        ].generate_embedding.return_value = [0.1, 0.2, 0.3]

        mock_llm_response = MagicMock()
        mock_llm_response.content = '{"narrative": "Test", "options": ["Option 1"], "state_changes": {"hp_change": 0}}'
        mock_llm_response.usage.total_tokens = 100
        mock_repositories["llm_service"].generate_response.return_value = (
            mock_llm_response
        )

        captured_system_prompt = None

        async def capture_llm_call(system_prompt, messages):
            nonlocal captured_system_prompt
            captured_system_prompt = system_prompt
            return mock_llm_response

        mock_repositories["llm_service"].generate_response.side_effect = (
            capture_llm_call
        )

        with patch(
            "app.game.domain.services.dice_service.random.randint"
        ) as mock_randint:
            mock_randint.return_value = 15

            use_case = ProcessActionUseCase(**mock_repositories)
            input_data = ProcessActionInput(
                session_id=active_session.id,
                action="attack",
                idempotency_key="test-key",
            )

            await use_case.execute(active_session.user_id, input_data)

        # Verify dice result in system prompt
        assert captured_system_prompt is not None
        assert (
            "주사위 판정 결과" in captured_system_prompt
            or "dice" in captured_system_prompt.lower()
        )


class TestDiceResultMapping:
    """Test mapping from DiceResult to DiceResultResponse."""

    def test_dice_result_fields_mapped_correctly(self):
        """Test all DiceResult fields are mapped to DiceResultResponse."""
        from app.game.presentation.routes.schemas.response import (
            DiceResultResponse,
        )

        dice_result = DiceResult(
            roll=15,
            modifier=3,
            dc=12,
            check_type=DiceCheckType.COMBAT,
            damage=8,
        )

        response = DiceResultResponse(
            roll=dice_result.roll,
            modifier=dice_result.modifier,
            total=dice_result.total,
            dc=dice_result.dc,
            is_success=dice_result.is_success,
            is_critical=dice_result.is_critical,
            is_fumble=dice_result.is_fumble,
            check_type=dice_result.check_type.value,
            damage=dice_result.damage,
            display_text=dice_result.display_text,
        )

        assert response.roll == 15
        assert response.modifier == 3
        assert response.total == 18
        assert response.dc == 12
        assert response.is_success is True
        assert response.is_critical is False
        assert response.is_fumble is False
        assert response.check_type == "combat"
        assert response.damage == 8
        assert "성공" in response.display_text
