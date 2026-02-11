"""Unit tests for GameState and StateChanges value objects."""

import pytest
from pydantic import ValidationError

from app.game.domain.value_objects import GameState, StateChanges


class TestGameState:
    """GameState value object tests."""

    def test_initialization_with_defaults(self):
        """Test GameState initializes with empty defaults."""
        state = GameState()

        assert state.items == []
        assert state.visited_locations == []
        assert state.met_npcs == []
        assert state.discoveries == []

    def test_initialization_with_values(self):
        """Test GameState initializes with provided values."""
        state = GameState(
            items=["sword", "torch"],
            visited_locations=["start", "forest"],
            met_npcs=["wizard"],
            discoveries=["secret_door"],
        )

        assert state.items == ["sword", "torch"]
        assert state.visited_locations == ["start", "forest"]
        assert state.met_npcs == ["wizard"]
        assert state.discoveries == ["secret_door"]

    def test_from_dict_with_empty_dict(self):
        """Test from_dict handles empty dictionary."""
        state = GameState.from_dict({})

        assert state.items == []
        assert state.visited_locations == []
        assert state.met_npcs == []
        assert state.discoveries == []

    def test_from_dict_with_partial_data(self):
        """Test from_dict handles partial dictionary."""
        state = GameState.from_dict(
            {"items": ["sword"], "met_npcs": ["wizard"]}
        )

        assert state.items == ["sword"]
        assert state.visited_locations == []
        assert state.met_npcs == ["wizard"]
        assert state.discoveries == []

    def test_from_dict_with_full_data(self):
        """Test from_dict handles full dictionary."""
        data = {
            "items": ["sword", "torch"],
            "visited_locations": ["start", "forest"],
            "met_npcs": ["wizard", "merchant"],
            "discoveries": ["secret_door"],
        }

        state = GameState.from_dict(data)

        assert state.items == ["sword", "torch"]
        assert state.visited_locations == ["start", "forest"]
        assert state.met_npcs == ["wizard", "merchant"]
        assert state.discoveries == ["secret_door"]

    def test_to_dict(self):
        """Test to_dict serializes correctly."""
        state = GameState(
            items=["sword"],
            visited_locations=["forest"],
            met_npcs=["wizard"],
            discoveries=["rune"],
        )

        result = state.to_dict()

        assert result == {
            "items": ["sword"],
            "visited_locations": ["forest"],
            "met_npcs": ["wizard"],
            "discoveries": ["rune"],
        }

    def test_immutability(self):
        """Test GameState is immutable (frozen)."""
        state = GameState(items=["sword"])

        with pytest.raises(ValidationError):
            state.items = ["torch"]

    def test_round_trip_serialization(self):
        """Test from_dict and to_dict are inverses."""
        original_data = {
            "items": ["sword", "torch", "potion"],
            "visited_locations": ["start", "forest", "cave"],
            "met_npcs": ["wizard", "merchant"],
            "discoveries": ["secret_door", "ancient_rune"],
        }

        state = GameState.from_dict(original_data)
        result = state.to_dict()

        assert result == original_data


class TestStateChanges:
    """StateChanges value object tests."""

    def test_initialization_with_defaults(self):
        """Test StateChanges initializes with defaults."""
        changes = StateChanges()

        assert changes.hp_change == 0
        assert changes.items_gained == []
        assert changes.items_lost == []
        assert changes.location is None
        assert changes.npcs_met == []
        assert changes.discoveries == []

    def test_initialization_with_values(self):
        """Test StateChanges initializes with provided values."""
        changes = StateChanges(
            hp_change=-10,
            items_gained=["sword"],
            items_lost=["torch"],
            location="cave",
            npcs_met=["wizard"],
            discoveries=["secret_door"],
        )

        assert changes.hp_change == -10
        assert changes.items_gained == ["sword"]
        assert changes.items_lost == ["torch"]
        assert changes.location == "cave"
        assert changes.npcs_met == ["wizard"]
        assert changes.discoveries == ["secret_door"]

    def test_immutability(self):
        """Test StateChanges is immutable (frozen)."""
        changes = StateChanges(items_gained=["sword"])

        with pytest.raises(ValidationError):
            changes.items_gained = ["torch"]

    def test_partial_changes(self):
        """Test StateChanges with only some fields set."""
        changes = StateChanges(items_gained=["sword"], location="armory")

        assert changes.items_gained == ["sword"]
        assert changes.location == "armory"
        assert changes.items_lost == []
        assert changes.hp_change == 0
        assert changes.npcs_met == []
        assert changes.discoveries == []

    def test_empty_changes(self):
        """Test StateChanges represents no-op when all defaults."""
        changes = StateChanges()

        assert changes.hp_change == 0
        assert not changes.items_gained
        assert not changes.items_lost
        assert changes.location is None
        assert not changes.npcs_met
        assert not changes.discoveries
