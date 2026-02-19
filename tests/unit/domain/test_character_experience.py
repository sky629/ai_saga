"""CharacterStats 경험치 시스템 단위 테스트."""

import pytest

from app.game.domain.entities.character import CharacterStats


class TestExperienceSystem:
    """경험치 및 레벨업 시스템 테스트."""

    def test_experience_for_next_level(self):
        """필요 경험치는 level × 100이어야 한다."""
        stats = CharacterStats(level=1)
        assert stats.experience_for_next_level() == 100

        stats = CharacterStats(level=2)
        assert stats.experience_for_next_level() == 200

        stats = CharacterStats(level=5)
        assert stats.experience_for_next_level() == 500

    def test_gain_experience_without_level_up(self):
        """레벨업 없이 경험치만 획득."""
        stats = CharacterStats(level=1, experience=0, current_experience=0)

        new_stats = stats.gain_experience(50)

        assert new_stats.level == 1
        assert new_stats.experience == 50
        assert new_stats.current_experience == 50

    def test_gain_experience_with_level_up(self):
        """경험치 획득으로 레벨업 발생."""
        # Lv1, 90 exp → +50 exp → Lv2
        stats = CharacterStats(
            level=1, hp=100, max_hp=100, experience=90, current_experience=90
        )

        new_stats = stats.gain_experience(50)  # 총 140 exp

        # Lv1→Lv2 (100 exp 소모)
        assert new_stats.level == 2
        assert new_stats.experience == 140
        assert new_stats.current_experience == 40  # 140 - 100
        assert new_stats.max_hp == 110  # 100 + (10 × 1)
        assert new_stats.hp == 110  # Full heal on level up

    def test_gain_experience_multiple_levels(self):
        """한 번에 여러 레벨 상승."""
        # Lv1 → +500 exp → Lv3
        stats = CharacterStats(
            level=1, hp=100, max_hp=100, experience=0, current_experience=0
        )

        new_stats = stats.gain_experience(500)

        # Lv1→Lv2 (100 exp), Lv2→Lv3 (200 exp), 총 300 exp 소모
        assert new_stats.level == 3
        assert new_stats.experience == 500
        assert new_stats.current_experience == 200  # 500 - 100 - 200

        # max_hp: 100 + 10 (Lv1→Lv2) + 20 (Lv2→Lv3) = 130
        assert new_stats.max_hp == 130
        assert new_stats.hp == 130

    def test_level_up_stat_increase_proportional(self):
        """레벨에 비례한 스탯 상승."""
        # Lv1→Lv2: +10 hp
        stats_lv1 = CharacterStats(level=1, max_hp=100)
        stats_lv2 = stats_lv1.level_up()
        assert stats_lv2.max_hp == 110  # 100 + 10 × 1

        # Lv2→Lv3: +20 hp
        stats_lv3 = stats_lv2.level_up()
        assert stats_lv3.max_hp == 130  # 110 + 10 × 2

        # Lv3→Lv4: +30 hp
        stats_lv4 = stats_lv3.level_up()
        assert stats_lv4.max_hp == 160  # 130 + 10 × 3

    def test_experience_fields_default_values(self):
        """경험치 필드 기본값."""
        stats = CharacterStats()
        assert stats.experience == 0
        assert stats.current_experience == 0

    def test_negative_experience_not_allowed(self):
        """음수 경험치는 허용되지 않음."""
        with pytest.raises(ValueError):
            CharacterStats(experience=-10)

        with pytest.raises(ValueError):
            CharacterStats(current_experience=-5)
