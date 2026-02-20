"""Unit tests for dice system integration in ProcessActionUseCase."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from app.game.application.use_cases.process_action import (
    ProcessActionInput,
    ProcessActionUseCase,
)
from app.game.domain.entities import CharacterEntity, CharacterStats
from app.game.domain.value_objects import ScenarioDifficulty, SessionStatus
from app.game.domain.value_objects.dice import DiceCheckType, DiceResult


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
        mock_llm_response.content = '{"narrative": "Test narrative", "options": ["Option 1"], "state_changes": {"hp_change": 0}}'
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
        assert result.response.dice_result.dc == 12  # NORMAL difficulty
        assert result.response.dice_result.is_success is True
        assert result.response.dice_result.check_type == "combat"

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
        mock_llm_response.content = '{"narrative": "Critical!", "options": ["Option 1"], "state_changes": {"hp_change": 0}}'
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
        mock_llm_response.content = '{"narrative": "Fumble!", "options": ["Option 1"], "state_changes": {"hp_change": 0}}'
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
    async def test_hp_zero_death(
        self, mock_repositories, active_session, character, scenario
    ):
        low_hp_character = CharacterEntity(
            id=character.id,
            user_id=character.user_id,
            scenario_id=character.scenario_id,
            name=character.name,
            description=character.description,
            stats=CharacterStats(hp=1, max_hp=100, level=5),
            inventory=[],
            is_active=True,
            created_at=character.created_at,
        )

        mock_repositories["cache_service"].get.return_value = None
        mock_repositories["session_repository"].get_by_id.return_value = (
            active_session
        )
        mock_repositories["character_repository"].get_by_id.return_value = (
            low_hp_character
        )
        mock_repositories["scenario_repository"].get_by_id.return_value = (
            scenario
        )
        mock_repositories[
            "embedding_service"
        ].generate_embedding.return_value = [0.1, 0.2, 0.3]

        mock_llm_response = MagicMock()
        mock_llm_response.content = '{"narrative": "Fumble!", "options": ["Option 1"], "state_changes": {"hp_change": 0}}'
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
