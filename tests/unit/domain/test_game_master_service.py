"""Unit tests for GameMasterService."""

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
                "experience_gained": 50,
                "items_gained": ["sword", "potion"],
                "items_lost": ["torch"],
                "location": "dungeon",
                "npcs_met": ["wizard", "merchant"],
                "discoveries": ["secret_door"],
            }
        }

        changes = GameMasterService.extract_state_changes(parsed)

        assert changes.hp_change == -10
        assert changes.experience_gained == 50
        assert changes.items_gained == ["sword", "potion"]
        assert changes.items_lost == ["torch"]
        assert changes.location == "dungeon"
        assert changes.npcs_met == ["wizard", "merchant"]
        assert changes.discoveries == ["secret_door"]

    def test_extract_state_changes_with_experience_gained(self):
        """Test extracting StateChanges with experience_gained field."""
        parsed = {
            "state_changes": {
                "experience_gained": 75,
            }
        }

        changes = GameMasterService.extract_state_changes(parsed)

        assert changes.experience_gained == 75
        assert changes.hp_change == 0  # default
        assert changes.items_gained == []  # default

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


class TestGameMasterServiceBeforeNarrative:
    """GameMasterService before_narrative 추출 테스트."""

    def test_extract_before_narrative_from_parsed_with_field(self):
        """before_narrative 필드가 있으면 해당 값을 반환."""
        parsed = {
            "before_narrative": "당신은 검을 들어올립니다.",
            "narrative": "검이 빛나며 적을 베었습니다!",
        }

        result = GameMasterService.extract_before_narrative_from_parsed(parsed)

        assert result == "당신은 검을 들어올립니다."

    def test_extract_before_narrative_from_parsed_missing_field(self):
        """before_narrative 필드가 없으면 None 반환."""
        parsed = {"narrative": "결과 서술"}

        result = GameMasterService.extract_before_narrative_from_parsed(parsed)

        assert result is None

    def test_extract_before_narrative_from_parsed_empty_string(self):
        """before_narrative가 빈 문자열이면 빈 문자열 반환."""
        parsed = {"before_narrative": "", "narrative": "결과"}

        result = GameMasterService.extract_before_narrative_from_parsed(parsed)

        assert result == ""


class TestGameMasterServiceDiceFiltering:
    """GameMasterService dice_applied extraction and state_changes filtering tests."""

    def test_extract_dice_applied_true(self):
        """dice_applied=true인 경우 True 반환."""
        parsed = {"dice_applied": True, "narrative": "Test"}
        result = GameMasterService.extract_dice_applied(parsed)
        assert result is True

    def test_extract_dice_applied_false(self):
        """dice_applied=false인 경우 False 반환."""
        parsed = {"dice_applied": False, "narrative": "Test"}
        result = GameMasterService.extract_dice_applied(parsed)
        assert result is False

    def test_extract_dice_applied_missing(self):
        """dice_applied 필드 없으면 False 반환 (safe default)."""
        parsed = {"narrative": "Test"}
        result = GameMasterService.extract_dice_applied(parsed)
        assert result is False

    def test_filter_state_changes_on_failure_blocks_location(self):
        """실패 시 location을 None으로 필터링."""
        changes = StateChanges(
            hp_change=-5,
            location="outside",
            items_gained=["sword"],
            items_lost=["torch"],
        )
        filtered = GameMasterService.filter_state_changes_on_dice_failure(
            changes
        )
        assert filtered.location is None

    def test_filter_state_changes_on_failure_blocks_items_gained(self):
        """실패 시 items_gained를 빈 리스트로 필터링."""
        changes = StateChanges(
            items_gained=["sword", "potion"],
            location="cave",
        )
        filtered = GameMasterService.filter_state_changes_on_dice_failure(
            changes
        )
        assert filtered.items_gained == []

    def test_filter_state_changes_on_failure_preserves_hp_change(self):
        """실패 시 hp_change는 유지."""
        changes = StateChanges(hp_change=-10, location="outside")
        filtered = GameMasterService.filter_state_changes_on_dice_failure(
            changes
        )
        assert filtered.hp_change == -10

    def test_filter_state_changes_on_failure_preserves_items_lost(self):
        """실패 시 items_lost는 유지."""
        changes = StateChanges(items_lost=["torch"], location="outside")
        filtered = GameMasterService.filter_state_changes_on_dice_failure(
            changes
        )
        assert filtered.items_lost == ["torch"]

    def test_filter_preserves_experience_and_discoveries(self):
        """실패 시 experience_gained, npcs_met, discoveries 유지."""
        changes = StateChanges(
            experience_gained=50,
            npcs_met=["wizard"],
            discoveries=["secret"],
            location="dungeon",
            items_gained=["key"],
        )
        filtered = GameMasterService.filter_state_changes_on_dice_failure(
            changes
        )
        assert filtered.experience_gained == 50
        assert filtered.npcs_met == ["wizard"]
        assert filtered.discoveries == ["secret"]
        assert filtered.location is None
        assert filtered.items_gained == []


class TestGameMasterServiceDeathCheck:
    """GameMasterService death check tests."""

    def test_should_end_game_by_death_when_hp_zero(self):
        """Test should_end_game_by_death returns True when HP=0."""
        from app.common.utils.datetime import get_utc_datetime
        from app.common.utils.id_generator import get_uuid7
        from app.game.domain.entities import CharacterEntity, CharacterStats

        stats = CharacterStats(hp=0, max_hp=100)
        character = CharacterEntity(
            id=get_uuid7(),
            user_id=get_uuid7(),
            scenario_id=get_uuid7(),
            name="Dead Character",
            stats=stats,
            created_at=get_utc_datetime(),
        )

        result = GameMasterService.should_end_game_by_death(character)

        assert result is True

    def test_should_end_game_by_death_when_hp_positive(self):
        """Test should_end_game_by_death returns False when HP>0."""
        from app.common.utils.datetime import get_utc_datetime
        from app.common.utils.id_generator import get_uuid7
        from app.game.domain.entities import CharacterEntity, CharacterStats

        stats = CharacterStats(hp=50, max_hp=100)
        character = CharacterEntity(
            id=get_uuid7(),
            user_id=get_uuid7(),
            scenario_id=get_uuid7(),
            name="Alive Character",
            stats=stats,
            created_at=get_utc_datetime(),
        )

        result = GameMasterService.should_end_game_by_death(character)

        assert result is False
