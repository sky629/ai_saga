"""Unit tests for Dice value objects."""

from app.game.domain.value_objects import DiceCheckType, DiceResult


class TestDiceCheckType:
    """DiceCheckType enum tests."""

    def test_dice_check_type_combat(self):
        """Test COMBAT check type exists."""
        assert DiceCheckType.COMBAT.value == "combat"

    def test_dice_check_type_skill(self):
        """Test SKILL check type exists."""
        assert DiceCheckType.SKILL.value == "skill"

    def test_dice_check_type_social(self):
        """Test SOCIAL check type exists."""
        assert DiceCheckType.SOCIAL.value == "social"

    def test_dice_check_type_exploration(self):
        """Test EXPLORATION check type exists."""
        assert DiceCheckType.EXPLORATION.value == "exploration"


class TestDiceResult:
    """DiceResult value object tests."""

    def test_dice_result_creation(self):
        """Test DiceResult can be created with basic fields."""
        result = DiceResult(
            roll=15,
            modifier=2,
            dc=12,
            check_type=DiceCheckType.COMBAT,
        )
        assert result.roll == 15
        assert result.modifier == 2
        assert result.total == 17
        assert result.dc == 12
        assert result.check_type == DiceCheckType.COMBAT

    def test_dice_result_total_calculation(self):
        """Test total is calculated as roll + modifier."""
        result = DiceResult(
            roll=10,
            modifier=5,
            dc=15,
            check_type=DiceCheckType.SKILL,
        )
        assert result.total == 15

    def test_dice_result_is_success_true(self):
        """Test is_success is True when total >= dc."""
        result = DiceResult(
            roll=15,
            modifier=2,
            dc=12,
            check_type=DiceCheckType.COMBAT,
        )
        assert result.is_success is True

    def test_dice_result_is_success_false(self):
        """Test is_success is False when total < dc."""
        result = DiceResult(
            roll=5,
            modifier=2,
            dc=12,
            check_type=DiceCheckType.COMBAT,
        )
        assert result.is_success is False

    def test_dice_result_is_success_equal(self):
        """Test is_success is True when total == dc."""
        result = DiceResult(
            roll=10,
            modifier=2,
            dc=12,
            check_type=DiceCheckType.COMBAT,
        )
        assert result.is_success is True

    def test_dice_result_is_critical_true(self):
        """Test is_critical is True when roll == 20."""
        result = DiceResult(
            roll=20,
            modifier=0,
            dc=10,
            check_type=DiceCheckType.COMBAT,
        )
        assert result.is_critical is True

    def test_dice_result_is_critical_false(self):
        """Test is_critical is False when roll != 20."""
        result = DiceResult(
            roll=19,
            modifier=0,
            dc=10,
            check_type=DiceCheckType.COMBAT,
        )
        assert result.is_critical is False

    def test_dice_result_is_fumble_true(self):
        """Test is_fumble is True when roll == 1."""
        result = DiceResult(
            roll=1,
            modifier=5,
            dc=10,
            check_type=DiceCheckType.COMBAT,
        )
        assert result.is_fumble is True

    def test_dice_result_is_fumble_false(self):
        """Test is_fumble is False when roll != 1."""
        result = DiceResult(
            roll=2,
            modifier=5,
            dc=10,
            check_type=DiceCheckType.COMBAT,
        )
        assert result.is_fumble is False

    def test_dice_result_with_damage(self):
        """Test DiceResult can include optional damage field."""
        result = DiceResult(
            roll=18,
            modifier=2,
            dc=12,
            check_type=DiceCheckType.COMBAT,
            damage=8,
        )
        assert result.damage == 8

    def test_dice_result_without_damage(self):
        """Test DiceResult damage defaults to None."""
        result = DiceResult(
            roll=15,
            modifier=2,
            dc=12,
            check_type=DiceCheckType.SKILL,
        )
        assert result.damage is None

    def test_dice_result_display_text_success(self):
        """Test display_text format for successful roll."""
        result = DiceResult(
            roll=15,
            modifier=2,
            dc=12,
            check_type=DiceCheckType.COMBAT,
        )
        display = result.display_text
        assert "🎲" in display
        assert "1d20+2" in display
        assert "17" in display
        assert "DC 12" in display
        assert "성공!" in display

    def test_dice_result_display_text_failure(self):
        """Test display_text format for failed roll."""
        result = DiceResult(
            roll=5,
            modifier=2,
            dc=12,
            check_type=DiceCheckType.COMBAT,
        )
        display = result.display_text
        assert "🎲" in display
        assert "1d20+2" in display
        assert "7" in display
        assert "DC 12" in display
        assert "실패..." in display

    def test_dice_result_display_text_critical(self):
        """Test display_text format for critical success."""
        result = DiceResult(
            roll=20,
            modifier=2,
            dc=12,
            check_type=DiceCheckType.COMBAT,
        )
        display = result.display_text
        assert "대성공!" in display

    def test_dice_result_display_text_fumble(self):
        """Test display_text format for fumble."""
        result = DiceResult(
            roll=1,
            modifier=2,
            dc=12,
            check_type=DiceCheckType.COMBAT,
        )
        display = result.display_text
        assert "대실패!" in display

    def test_dice_result_immutability(self):
        """Test DiceResult is frozen (immutable)."""
        result = DiceResult(
            roll=15,
            modifier=2,
            dc=12,
            check_type=DiceCheckType.COMBAT,
        )
        try:
            result.roll = 10
            assert False, "Should not be able to modify frozen model"
        except Exception:
            pass  # Expected

    def test_dice_result_negative_modifier(self):
        """Test DiceResult with negative modifier."""
        result = DiceResult(
            roll=10,
            modifier=-3,
            dc=8,
            check_type=DiceCheckType.SKILL,
        )
        assert result.total == 7
        assert result.is_success is False

    def test_dice_result_zero_modifier(self):
        """Test DiceResult with zero modifier."""
        result = DiceResult(
            roll=12,
            modifier=0,
            dc=12,
            check_type=DiceCheckType.EXPLORATION,
        )
        assert result.total == 12
        assert result.is_success is True

    def test_dice_result_all_check_types(self):
        """Test DiceResult works with all check types."""
        for check_type in DiceCheckType:
            result = DiceResult(
                roll=15,
                modifier=2,
                dc=12,
                check_type=check_type,
            )
            assert result.check_type == check_type
