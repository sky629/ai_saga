"""UserProgressionService 단위 테스트."""

from app.game.domain.services.user_progression_service import (
    UserProgressionService,
)
from app.game.domain.value_objects import EndingType, ScenarioDifficulty


class TestUserProgressionServiceCalculateXp:
    """XP 계산 테스트."""

    def test_calculate_xp_victory_normal(self):
        xp = UserProgressionService.calculate_game_xp(
            EndingType.VICTORY,
            turn_count=10,
            difficulty=ScenarioDifficulty.NORMAL,
        )
        assert xp == 300  # 200 + 10*10

    def test_calculate_xp_defeat_normal(self):
        xp = UserProgressionService.calculate_game_xp(
            EndingType.DEFEAT,
            turn_count=5,
            difficulty=ScenarioDifficulty.NORMAL,
        )
        assert xp == 75  # 50 + 5*5

    def test_calculate_xp_neutral_normal(self):
        xp = UserProgressionService.calculate_game_xp(
            EndingType.NEUTRAL,
            turn_count=7,
            difficulty=ScenarioDifficulty.NORMAL,
        )
        assert xp == 149  # 100 + 7*7

    def test_calculate_xp_hard_difficulty_bonus(self):
        xp = UserProgressionService.calculate_game_xp(
            EndingType.VICTORY,
            turn_count=10,
            difficulty=ScenarioDifficulty.HARD,
        )
        assert xp == int(300 * 1.5)  # 450

    def test_calculate_xp_nightmare_difficulty_bonus(self):
        xp = UserProgressionService.calculate_game_xp(
            EndingType.VICTORY,
            turn_count=10,
            difficulty=ScenarioDifficulty.NIGHTMARE,
        )
        assert xp == int(300 * 1.5)  # 450

    def test_calculate_xp_easy_no_bonus(self):
        xp = UserProgressionService.calculate_game_xp(
            EndingType.VICTORY,
            turn_count=10,
            difficulty=ScenarioDifficulty.EASY,
        )
        assert xp == 300  # 보너스 없음

    def test_calculate_xp_zero_turns(self):
        xp = UserProgressionService.calculate_game_xp(
            EndingType.VICTORY,
            turn_count=0,
            difficulty=ScenarioDifficulty.NORMAL,
        )
        assert xp == 200  # base만


class TestUserProgressionServiceStartingHp:
    """시작 HP 계산 테스트."""

    def test_calculate_starting_hp_level_1(self):
        assert UserProgressionService.calculate_starting_hp(1) == 100

    def test_calculate_starting_hp_level_3(self):
        assert UserProgressionService.calculate_starting_hp(3) == 120

    def test_calculate_starting_hp_level_5(self):
        assert UserProgressionService.calculate_starting_hp(5) == 140

    def test_calculate_starting_hp_level_10(self):
        assert UserProgressionService.calculate_starting_hp(10) == 190
