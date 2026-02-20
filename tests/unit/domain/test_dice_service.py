"""Unit tests for DiceService domain service."""

from unittest.mock import patch

from app.game.domain.services import DiceService
from app.game.domain.value_objects import ScenarioDifficulty
from app.game.domain.value_objects.dice import DiceCheckType


class TestDiceServiceRollD20:
    """roll_d20 method tests."""

    def test_roll_d20_returns_int(self):
        """Test roll_d20 returns an integer."""
        result = DiceService.roll_d20()
        assert isinstance(result, int)

    def test_roll_d20_range(self):
        """Test roll_d20 returns value between 1 and 20."""
        with patch(
            "app.game.domain.services.dice_service.random.randint"
        ) as mock_randint:
            mock_randint.return_value = 1
            assert DiceService.roll_d20() == 1

            mock_randint.return_value = 20
            assert DiceService.roll_d20() == 20

            mock_randint.return_value = 10
            assert DiceService.roll_d20() == 10


class TestDiceServiceCalculateModifier:
    """calculate_modifier method tests."""

    def test_calculate_modifier_level_1(self):
        """Test level 1 gives +2 modifier."""
        assert DiceService.calculate_modifier(1) == 2

    def test_calculate_modifier_level_4(self):
        """Test level 4 gives +2 modifier."""
        assert DiceService.calculate_modifier(4) == 2

    def test_calculate_modifier_level_5(self):
        """Test level 5 gives +3 modifier."""
        assert DiceService.calculate_modifier(5) == 3

    def test_calculate_modifier_level_8(self):
        """Test level 8 gives +3 modifier."""
        assert DiceService.calculate_modifier(8) == 3

    def test_calculate_modifier_level_9(self):
        """Test level 9 gives +4 modifier."""
        assert DiceService.calculate_modifier(9) == 4

    def test_calculate_modifier_level_12(self):
        """Test level 12 gives +4 modifier."""
        assert DiceService.calculate_modifier(12) == 4

    def test_calculate_modifier_level_13(self):
        """Test level 13 gives +5 modifier."""
        assert DiceService.calculate_modifier(13) == 5


class TestDiceServiceGetDC:
    """get_dc method tests."""

    def test_get_dc_easy(self):
        """Test EASY difficulty returns DC 8."""
        assert DiceService.get_dc(ScenarioDifficulty.EASY) == 8

    def test_get_dc_normal(self):
        """Test NORMAL difficulty returns DC 12."""
        assert DiceService.get_dc(ScenarioDifficulty.NORMAL) == 12

    def test_get_dc_hard(self):
        """Test HARD difficulty returns DC 15."""
        assert DiceService.get_dc(ScenarioDifficulty.HARD) == 15

    def test_get_dc_nightmare(self):
        """Test NIGHTMARE difficulty returns DC 18."""
        assert DiceService.get_dc(ScenarioDifficulty.NIGHTMARE) == 18


class TestDiceServiceGetDamageDice:
    """get_damage_dice method tests."""

    def test_get_damage_dice_level_1(self):
        """Test level 1 returns 1d4."""
        assert DiceService.get_damage_dice(1) == (1, 4)

    def test_get_damage_dice_level_2(self):
        """Test level 2 returns 1d4."""
        assert DiceService.get_damage_dice(2) == (1, 4)

    def test_get_damage_dice_level_3(self):
        """Test level 3 returns 1d6."""
        assert DiceService.get_damage_dice(3) == (1, 6)

    def test_get_damage_dice_level_4(self):
        """Test level 4 returns 1d6."""
        assert DiceService.get_damage_dice(4) == (1, 6)

    def test_get_damage_dice_level_5(self):
        """Test level 5 returns 1d8."""
        assert DiceService.get_damage_dice(5) == (1, 8)

    def test_get_damage_dice_level_6(self):
        """Test level 6 returns 1d8."""
        assert DiceService.get_damage_dice(6) == (1, 8)

    def test_get_damage_dice_level_7(self):
        """Test level 7 returns 1d10."""
        assert DiceService.get_damage_dice(7) == (1, 10)

    def test_get_damage_dice_level_8(self):
        """Test level 8 returns 1d10."""
        assert DiceService.get_damage_dice(8) == (1, 10)

    def test_get_damage_dice_level_9(self):
        """Test level 9 returns 1d12."""
        assert DiceService.get_damage_dice(9) == (1, 12)

    def test_get_damage_dice_level_20(self):
        """Test high level returns 1d12."""
        assert DiceService.get_damage_dice(20) == (1, 12)


class TestDiceServiceRollDamage:
    """roll_damage method tests."""

    def test_roll_damage_normal(self):
        """Test normal damage roll."""
        with patch(
            "app.game.domain.services.dice_service.random.randint"
        ) as mock_randint:
            mock_randint.return_value = 4
            result = DiceService.roll_damage(1, is_critical=False)
            assert result == 4

    def test_roll_damage_critical(self):
        """Test critical damage rolls double dice."""
        with patch(
            "app.game.domain.services.dice_service.random.randint"
        ) as mock_randint:
            mock_randint.return_value = 3
            result = DiceService.roll_damage(1, is_critical=True)
            assert result == 6


class TestDiceServiceRollFumbleDamage:
    """roll_fumble_damage method tests."""

    def test_roll_fumble_damage(self):
        """Test fumble damage is 1d4."""
        with patch(
            "app.game.domain.services.dice_service.random.randint"
        ) as mock_randint:
            mock_randint.return_value = 2
            result = DiceService.roll_fumble_damage()
            assert result == 2


class TestDiceServicePerformCheck:
    """perform_check method tests."""

    def test_perform_check_returns_dice_result(self):
        """Test perform_check returns a DiceResult."""
        with patch(
            "app.game.domain.services.dice_service.random.randint"
        ) as mock_randint:
            mock_randint.return_value = 15
            result = DiceService.perform_check(
                level=5,
                difficulty=ScenarioDifficulty.NORMAL,
                check_type=DiceCheckType.COMBAT,
            )
            assert result.roll == 15
            assert result.modifier == 3
            assert result.dc == 12
            assert result.check_type == DiceCheckType.COMBAT

    def test_perform_check_critical(self):
        """Test perform_check with critical hit (roll=20)."""
        with patch(
            "app.game.domain.services.dice_service.random.randint"
        ) as mock_randint:
            mock_randint.side_effect = [20, 5, 3]
            result = DiceService.perform_check(
                level=5,
                difficulty=ScenarioDifficulty.NORMAL,
                check_type=DiceCheckType.COMBAT,
            )
            assert result.is_critical is True
            assert result.damage is not None
            assert result.damage == 8

    def test_perform_check_fumble(self):
        """Test perform_check with fumble (roll=1)."""
        with patch(
            "app.game.domain.services.dice_service.random.randint"
        ) as mock_randint:
            mock_randint.return_value = 1
            result = DiceService.perform_check(
                level=5,
                difficulty=ScenarioDifficulty.NORMAL,
                check_type=DiceCheckType.COMBAT,
            )
            assert result.is_fumble is True
            assert result.damage is not None

    def test_perform_check_success(self):
        """Test perform_check with success (total >= dc)."""
        with patch(
            "app.game.domain.services.dice_service.random.randint"
        ) as mock_randint:
            mock_randint.return_value = 15
            result = DiceService.perform_check(
                level=5,
                difficulty=ScenarioDifficulty.NORMAL,
                check_type=DiceCheckType.COMBAT,
            )
            assert result.is_success is True

    def test_perform_check_failure(self):
        """Test perform_check with failure (total < dc)."""
        with patch(
            "app.game.domain.services.dice_service.random.randint"
        ) as mock_randint:
            mock_randint.return_value = 5
            result = DiceService.perform_check(
                level=5,
                difficulty=ScenarioDifficulty.NORMAL,
                check_type=DiceCheckType.COMBAT,
            )
            assert result.is_success is False

    def test_perform_check_all_types(self):
        """Test perform_check works with all check types."""
        for check_type in DiceCheckType:
            with patch(
                "app.game.domain.services.dice_service.random.randint"
            ) as mock_randint:
                mock_randint.return_value = 15
                result = DiceService.perform_check(
                    level=5,
                    difficulty=ScenarioDifficulty.NORMAL,
                    check_type=check_type,
                )
                assert result.check_type == check_type

    def test_perform_check_all_difficulties(self):
        """Test perform_check works with all difficulties."""
        for difficulty in ScenarioDifficulty:
            with patch(
                "app.game.domain.services.dice_service.random.randint"
            ) as mock_randint:
                mock_randint.return_value = 15
                result = DiceService.perform_check(
                    level=5,
                    difficulty=difficulty,
                    check_type=DiceCheckType.COMBAT,
                )
                assert result.dc == DiceService.get_dc(difficulty)
