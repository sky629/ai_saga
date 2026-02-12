"""Unit tests for GameSession entity."""

from app.common.utils.datetime import get_utc_datetime
from app.common.utils.id_generator import get_uuid7
from app.game.domain.entities import GameSessionEntity
from app.game.domain.value_objects import (
    EndingType,
    GameState,
    SessionStatus,
    StateChanges,
)


class TestGameSessionEntity:
    """GameSession entity tests."""

    def test_update_game_state_with_items_gained(self):
        """Test update_game_state adds items to inventory."""
        session = GameSessionEntity(
            id=get_uuid7(),
            user_id=get_uuid7(),
            character_id=get_uuid7(),
            scenario_id=get_uuid7(),
            current_location="start",
            game_state={},
            status=SessionStatus.ACTIVE,
            turn_count=0,
            max_turns=30,
            started_at=get_utc_datetime(),
            last_activity_at=get_utc_datetime(),
        )

        changes = StateChanges(items_gained=["sword"])
        updated = session.update_game_state(changes)

        assert updated.id == session.id
        assert updated.game_state != session.game_state
        state = GameState.from_dict(updated.game_state)
        assert "sword" in state.items

    def test_update_game_state_preserves_existing_items(self):
        """Test update_game_state preserves existing state."""
        session = GameSessionEntity(
            id=get_uuid7(),
            user_id=get_uuid7(),
            character_id=get_uuid7(),
            scenario_id=get_uuid7(),
            current_location="start",
            game_state={"items": ["torch"]},
            status=SessionStatus.ACTIVE,
            turn_count=0,
            max_turns=30,
            started_at=get_utc_datetime(),
            last_activity_at=get_utc_datetime(),
        )

        changes = StateChanges(items_gained=["sword"])
        updated = session.update_game_state(changes)

        state = GameState.from_dict(updated.game_state)
        assert "torch" in state.items
        assert "sword" in state.items

    def test_update_game_state_with_location(self):
        """Test update_game_state updates visited_locations."""
        session = GameSessionEntity(
            id=get_uuid7(),
            user_id=get_uuid7(),
            character_id=get_uuid7(),
            scenario_id=get_uuid7(),
            current_location="start",
            game_state={},
            status=SessionStatus.ACTIVE,
            turn_count=0,
            max_turns=30,
            started_at=get_utc_datetime(),
            last_activity_at=get_utc_datetime(),
        )

        changes = StateChanges(location="forest")
        updated = session.update_game_state(changes)

        state = GameState.from_dict(updated.game_state)
        assert "forest" in state.visited_locations

    def test_update_game_state_with_npcs(self):
        """Test update_game_state adds NPCs to met_npcs."""
        session = GameSessionEntity(
            id=get_uuid7(),
            user_id=get_uuid7(),
            character_id=get_uuid7(),
            scenario_id=get_uuid7(),
            current_location="start",
            game_state={},
            status=SessionStatus.ACTIVE,
            turn_count=0,
            max_turns=30,
            started_at=get_utc_datetime(),
            last_activity_at=get_utc_datetime(),
        )

        changes = StateChanges(npcs_met=["wizard"])
        updated = session.update_game_state(changes)

        state = GameState.from_dict(updated.game_state)
        assert "wizard" in state.met_npcs

    def test_update_game_state_with_discoveries(self):
        """Test update_game_state adds discoveries."""
        session = GameSessionEntity(
            id=get_uuid7(),
            user_id=get_uuid7(),
            character_id=get_uuid7(),
            scenario_id=get_uuid7(),
            current_location="start",
            game_state={},
            status=SessionStatus.ACTIVE,
            turn_count=0,
            max_turns=30,
            started_at=get_utc_datetime(),
            last_activity_at=get_utc_datetime(),
        )

        changes = StateChanges(discoveries=["secret_door"])
        updated = session.update_game_state(changes)

        state = GameState.from_dict(updated.game_state)
        assert "secret_door" in state.discoveries

    def test_update_game_state_with_items_lost(self):
        """Test update_game_state removes items."""
        session = GameSessionEntity(
            id=get_uuid7(),
            user_id=get_uuid7(),
            character_id=get_uuid7(),
            scenario_id=get_uuid7(),
            current_location="start",
            game_state={"items": ["torch", "sword"]},
            status=SessionStatus.ACTIVE,
            turn_count=0,
            max_turns=30,
            started_at=get_utc_datetime(),
            last_activity_at=get_utc_datetime(),
        )

        changes = StateChanges(items_lost=["torch"])
        updated = session.update_game_state(changes)

        state = GameState.from_dict(updated.game_state)
        assert "torch" not in state.items
        assert "sword" in state.items

    def test_update_game_state_updates_last_activity(self):
        """Test update_game_state updates last_activity_at."""
        session = GameSessionEntity(
            id=get_uuid7(),
            user_id=get_uuid7(),
            character_id=get_uuid7(),
            scenario_id=get_uuid7(),
            current_location="start",
            game_state={},
            status=SessionStatus.ACTIVE,
            turn_count=0,
            max_turns=30,
            started_at=get_utc_datetime(),
            last_activity_at=get_utc_datetime(),
        )

        changes = StateChanges(items_gained=["sword"])
        updated = session.update_game_state(changes)

        assert updated.last_activity_at >= session.last_activity_at

    def test_update_game_state_returns_new_instance(self):
        """Test update_game_state returns new instance (immutable)."""
        session = GameSessionEntity(
            id=get_uuid7(),
            user_id=get_uuid7(),
            character_id=get_uuid7(),
            scenario_id=get_uuid7(),
            current_location="start",
            game_state={},
            status=SessionStatus.ACTIVE,
            turn_count=0,
            max_turns=30,
            started_at=get_utc_datetime(),
            last_activity_at=get_utc_datetime(),
        )

        changes = StateChanges(items_gained=["sword"])
        updated = session.update_game_state(changes)

        assert updated is not session
        assert session.game_state == {}  # Original unchanged

    def test_update_game_state_with_complex_changes(self):
        """Test update_game_state with multiple changes."""
        session = GameSessionEntity(
            id=get_uuid7(),
            user_id=get_uuid7(),
            character_id=get_uuid7(),
            scenario_id=get_uuid7(),
            current_location="start",
            game_state={"items": ["torch"]},
            status=SessionStatus.ACTIVE,
            turn_count=0,
            max_turns=30,
            started_at=get_utc_datetime(),
            last_activity_at=get_utc_datetime(),
        )

        changes = StateChanges(
            items_gained=["sword", "potion"],
            location="cave",
            npcs_met=["wizard", "merchant"],
            discoveries=["secret_door"],
        )
        updated = session.update_game_state(changes)

        state = GameState.from_dict(updated.game_state)
        assert "torch" in state.items
        assert "sword" in state.items
        assert "potion" in state.items
        assert "cave" in state.visited_locations
        assert "wizard" in state.met_npcs
        assert "merchant" in state.met_npcs
        assert "secret_door" in state.discoveries


class TestExistingGameSessionMethods:
    """Tests for existing GameSession methods to ensure they still work."""

    def test_advance_turn(self):
        """Test advance_turn increments turn count."""
        session = GameSessionEntity(
            id=get_uuid7(),
            user_id=get_uuid7(),
            character_id=get_uuid7(),
            scenario_id=get_uuid7(),
            current_location="start",
            game_state={},
            status=SessionStatus.ACTIVE,
            turn_count=0,
            max_turns=30,
            started_at=get_utc_datetime(),
            last_activity_at=get_utc_datetime(),
        )

        updated = session.advance_turn()

        assert updated.turn_count == 1
        assert updated.id == session.id

    def test_complete(self):
        """Test complete sets status and ending."""
        session = GameSessionEntity(
            id=get_uuid7(),
            user_id=get_uuid7(),
            character_id=get_uuid7(),
            scenario_id=get_uuid7(),
            current_location="start",
            game_state={},
            status=SessionStatus.ACTIVE,
            turn_count=0,
            max_turns=30,
            started_at=get_utc_datetime(),
            last_activity_at=get_utc_datetime(),
        )

        updated = session.complete(EndingType.VICTORY)

        assert updated.status == SessionStatus.COMPLETED
        assert updated.ending_type == EndingType.VICTORY
        assert updated.ended_at is not None

    def test_update_location(self):
        """Test update_location changes current_location."""
        session = GameSessionEntity(
            id=get_uuid7(),
            user_id=get_uuid7(),
            character_id=get_uuid7(),
            scenario_id=get_uuid7(),
            current_location="start",
            game_state={},
            status=SessionStatus.ACTIVE,
            turn_count=0,
            max_turns=30,
            started_at=get_utc_datetime(),
            last_activity_at=get_utc_datetime(),
        )

        updated = session.update_location("forest")

        assert updated.current_location == "forest"
        assert session.current_location == "start"
