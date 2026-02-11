"""Unit tests for GameMasterService."""

import pytest

from app.game.domain.services import GameMasterService
from app.game.domain.value_objects import StateChanges


class TestGameMasterServiceJSONParsing:
    """GameMasterService JSON parsing tests."""

    def test_parse_llm_response_valid_json_with_markdown(self):
        """Test parsing valid JSON wrapped in markdown code block."""
        response = """```json
{
    "narrative": "You find a sword!",
    "options": ["Take it", "Leave it"],
    "state_changes": {
        "items_gained": ["sword"],
        "location": "armory"
    }
}
```"""

        result = GameMasterService.parse_llm_response(response)

        assert result is not None
        assert result["narrative"] == "You find a sword!"
        assert result["options"] == ["Take it", "Leave it"]
        assert result["state_changes"]["items_gained"] == ["sword"]
        assert result["state_changes"]["location"] == "armory"

    def test_parse_llm_response_valid_json_without_markdown(self):
        """Test parsing valid JSON without markdown wrapper."""
        response = """{
    "narrative": "Test narrative",
    "options": ["Option 1"]
}"""

        result = GameMasterService.parse_llm_response(response)

        assert result is not None
        assert result["narrative"] == "Test narrative"
        assert result["options"] == ["Option 1"]

    def test_parse_llm_response_malformed_returns_none(self):
        """Test malformed JSON returns None."""
        response = "This is not JSON"

        result = GameMasterService.parse_llm_response(response)

        assert result is None

    def test_parse_llm_response_empty_string_returns_none(self):
        """Test empty string returns None."""
        response = ""

        result = GameMasterService.parse_llm_response(response)

        assert result is None

    def test_parse_llm_response_incomplete_json_returns_none(self):
        """Test incomplete JSON returns None."""
        response = '{"narrative": "test"'

        result = GameMasterService.parse_llm_response(response)

        assert result is None

    def test_parse_llm_response_with_extra_text_before_json(self):
        """Test JSON parsing ignores text before code block."""
        response = """Here's the response:
```json
{
    "narrative": "Test"
}
```"""

        result = GameMasterService.parse_llm_response(response)

        assert result is not None
        assert result["narrative"] == "Test"

    def test_parse_llm_response_with_extra_text_after_json(self):
        """Test JSON parsing ignores text after code block."""
        response = """```json
{
    "narrative": "Test"
}
```
Some extra text here"""

        result = GameMasterService.parse_llm_response(response)

        assert result is not None
        assert result["narrative"] == "Test"

    def test_extract_state_changes_from_parsed(self):
        """Test extracting StateChanges from parsed JSON."""
        parsed = {
            "state_changes": {
                "items_gained": ["sword"],
                "location": "cave",
                "npcs_met": ["wizard"],
            }
        }

        changes = GameMasterService.extract_state_changes(parsed)

        assert isinstance(changes, StateChanges)
        assert "sword" in changes.items_gained
        assert changes.location == "cave"
        assert "wizard" in changes.npcs_met

    def test_extract_state_changes_with_empty_state_changes(self):
        """Test extracting StateChanges when state_changes is empty."""
        parsed = {"state_changes": {}}

        changes = GameMasterService.extract_state_changes(parsed)

        assert isinstance(changes, StateChanges)
        assert changes.items_gained == []
        assert changes.location is None

    def test_extract_state_changes_without_state_changes_field(self):
        """Test extracting StateChanges when field is missing."""
        parsed = {"narrative": "Test"}

        changes = GameMasterService.extract_state_changes(parsed)

        assert isinstance(changes, StateChanges)
        assert changes.items_gained == []

    def test_extract_state_changes_with_all_fields(self):
        """Test extracting StateChanges with all possible fields."""
        parsed = {
            "state_changes": {
                "hp_change": -10,
                "items_gained": ["sword", "potion"],
                "items_lost": ["torch"],
                "location": "dungeon",
                "npcs_met": ["wizard", "merchant"],
                "discoveries": ["secret_door"],
            }
        }

        changes = GameMasterService.extract_state_changes(parsed)

        assert changes.hp_change == -10
        assert changes.items_gained == ["sword", "potion"]
        assert changes.items_lost == ["torch"]
        assert changes.location == "dungeon"
        assert changes.npcs_met == ["wizard", "merchant"]
        assert changes.discoveries == ["secret_door"]

    def test_extract_narrative_from_parsed(self):
        """Test extracting narrative from parsed JSON."""
        parsed = {"narrative": "You enter a dark cave."}

        result = GameMasterService.extract_narrative_from_parsed(
            parsed, "fallback"
        )

        assert result == "You enter a dark cave."

    def test_extract_narrative_from_parsed_uses_fallback(self):
        """Test fallback is used when narrative is missing."""
        parsed = {"options": ["Go north"]}

        result = GameMasterService.extract_narrative_from_parsed(
            parsed, "fallback text"
        )

        assert result == "fallback text"

    def test_extract_options_from_parsed(self):
        """Test extracting options from parsed JSON."""
        parsed = {"options": ["Option 1", "Option 2", "Option 3"]}

        result = GameMasterService.extract_options_from_parsed(parsed)

        assert result == ["Option 1", "Option 2", "Option 3"]

    def test_extract_options_from_parsed_missing_field(self):
        """Test extracting options returns empty list when missing."""
        parsed = {"narrative": "Test"}

        result = GameMasterService.extract_options_from_parsed(parsed)

        assert result == []

    def test_extract_options_from_parsed_empty_list(self):
        """Test extracting options handles empty list."""
        parsed = {"options": []}

        result = GameMasterService.extract_options_from_parsed(parsed)

        assert result == []
