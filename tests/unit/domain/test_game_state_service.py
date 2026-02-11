"""Unit tests for GameStateService."""

import pytest

from app.game.domain.services import GameStateService
from app.game.domain.value_objects import GameState, StateChanges


class TestGameStateService:
    """GameStateService tests."""

    def test_apply_state_changes_to_empty_state(self):
        """Test applying changes to empty state."""
        current = {}
        changes = StateChanges(items_gained=["sword"], location="forest")

        result = GameStateService.apply_state_changes(current, changes)

        assert "sword" in result["items"]
        assert "forest" in result["visited_locations"]

    def test_apply_state_changes_appends_items(self):
        """Test items_gained appends to existing items."""
        current = {"items": ["torch"]}
        changes = StateChanges(items_gained=["sword"])

        result = GameStateService.apply_state_changes(current, changes)

        assert "torch" in result["items"]
        assert "sword" in result["items"]

    def test_apply_state_changes_removes_items(self):
        """Test items_lost removes items from inventory."""
        current = {"items": ["torch", "sword"]}
        changes = StateChanges(items_lost=["torch"])

        result = GameStateService.apply_state_changes(current, changes)

        assert "torch" not in result["items"]
        assert "sword" in result["items"]

    def test_apply_state_changes_removes_nonexistent_item_safely(self):
        """Test removing item that doesn't exist doesn't error."""
        current = {"items": ["sword"]}
        changes = StateChanges(items_lost=["torch"])

        result = GameStateService.apply_state_changes(current, changes)

        assert "sword" in result["items"]
        assert result["items"] == ["sword"]

    def test_apply_state_changes_deduplicates_items(self):
        """Test adding duplicate items doesn't create duplicates."""
        current = {"items": ["torch"]}
        changes = StateChanges(items_gained=["torch"])

        result = GameStateService.apply_state_changes(current, changes)

        assert result["items"].count("torch") == 1

    def test_apply_state_changes_adds_location(self):
        """Test new location is added to visited_locations."""
        current = {"visited_locations": ["start"]}
        changes = StateChanges(location="forest")

        result = GameStateService.apply_state_changes(current, changes)

        assert "start" in result["visited_locations"]
        assert "forest" in result["visited_locations"]

    def test_apply_state_changes_deduplicates_locations(self):
        """Test visiting same location doesn't duplicate."""
        current = {"visited_locations": ["forest"]}
        changes = StateChanges(location="forest")

        result = GameStateService.apply_state_changes(current, changes)

        assert result["visited_locations"].count("forest") == 1

    def test_apply_state_changes_adds_npcs(self):
        """Test new NPCs are added to met_npcs."""
        current = {"met_npcs": ["wizard"]}
        changes = StateChanges(npcs_met=["merchant", "guard"])

        result = GameStateService.apply_state_changes(current, changes)

        assert "wizard" in result["met_npcs"]
        assert "merchant" in result["met_npcs"]
        assert "guard" in result["met_npcs"]

    def test_apply_state_changes_deduplicates_npcs(self):
        """Test meeting same NPC doesn't duplicate."""
        current = {"met_npcs": ["wizard"]}
        changes = StateChanges(npcs_met=["wizard"])

        result = GameStateService.apply_state_changes(current, changes)

        assert result["met_npcs"].count("wizard") == 1

    def test_apply_state_changes_adds_discoveries(self):
        """Test discoveries are added."""
        current = {"discoveries": ["secret_door"]}
        changes = StateChanges(discoveries=["ancient_rune"])

        result = GameStateService.apply_state_changes(current, changes)

        assert "secret_door" in result["discoveries"]
        assert "ancient_rune" in result["discoveries"]

    def test_apply_state_changes_deduplicates_discoveries(self):
        """Test same discovery doesn't duplicate."""
        current = {"discoveries": ["secret_door"]}
        changes = StateChanges(discoveries=["secret_door"])

        result = GameStateService.apply_state_changes(current, changes)

        assert result["discoveries"].count("secret_door") == 1

    def test_apply_state_changes_preserves_all_fields(self):
        """Test all state fields are preserved."""
        current = {
            "items": ["torch"],
            "visited_locations": ["start"],
            "met_npcs": ["wizard"],
            "discoveries": ["clue1"],
        }
        changes = StateChanges(items_gained=["sword"])

        result = GameStateService.apply_state_changes(current, changes)

        assert "torch" in result["items"]
        assert "sword" in result["items"]
        assert "start" in result["visited_locations"]
        assert "wizard" in result["met_npcs"]
        assert "clue1" in result["discoveries"]

    def test_apply_state_changes_with_multiple_changes(self):
        """Test applying multiple changes at once."""
        current = {"items": ["torch"]}
        changes = StateChanges(
            items_gained=["sword", "potion"],
            items_lost=["torch"],
            location="cave",
            npcs_met=["merchant"],
            discoveries=["treasure_map"],
        )

        result = GameStateService.apply_state_changes(current, changes)

        assert "torch" not in result["items"]
        assert "sword" in result["items"]
        assert "potion" in result["items"]
        assert "cave" in result["visited_locations"]
        assert "merchant" in result["met_npcs"]
        assert "treasure_map" in result["discoveries"]

    def test_apply_state_changes_with_no_changes(self):
        """Test applying empty changes returns unchanged state."""
        current = {
            "items": ["sword"],
            "visited_locations": ["forest"],
            "met_npcs": ["wizard"],
            "discoveries": ["clue1"],
        }
        changes = StateChanges()

        result = GameStateService.apply_state_changes(current, changes)

        assert result["items"] == ["sword"]
        assert result["visited_locations"] == ["forest"]
        assert result["met_npcs"] == ["wizard"]
        assert result["discoveries"] == ["clue1"]

    def test_apply_state_changes_ignores_hp_change(self):
        """Test hp_change is in StateChanges but not persisted to GameState."""
        current = {}
        changes = StateChanges(hp_change=-10, items_gained=["sword"])

        result = GameStateService.apply_state_changes(current, changes)

        assert "hp_change" not in result
        assert "sword" in result["items"]
