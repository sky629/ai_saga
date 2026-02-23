"""UserEntity 게임 레벨/경험치 관련 단위 테스트."""

from datetime import datetime, timezone

import pytest

from app.auth.domain.entities.user import UserEntity
from app.auth.domain.value_objects import UserLevel
from app.common.utils.id_generator import get_uuid7


def _make_user(
    game_level: int = 1,
    game_experience: int = 0,
    game_current_experience: int = 0,
) -> UserEntity:
    """테스트용 UserEntity 생성 헬퍼."""
    return UserEntity(
        id=get_uuid7(),
        email="test@example.com",
        name="테스트유저",
        user_level=UserLevel.NORMAL,
        game_level=game_level,
        game_experience=game_experience,
        game_current_experience=game_current_experience,
        is_active=True,
        email_verified=False,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


class TestUserEntityGameLevel:
    """UserEntity 게임 레벨/경험치 테스트."""

    def test_default_game_level_is_1(self):
        """기본 게임 레벨은 1이어야 한다."""
        user = _make_user()
        assert user.game_level == 1

    def test_default_game_experience_is_0(self):
        """기본 게임 경험치는 0이어야 한다."""
        user = _make_user()
        assert user.game_experience == 0
        assert user.game_current_experience == 0

    def test_game_experience_for_next_level_lv1(self):
        """Lv1 → Lv2 필요 경험치: 300."""
        user = _make_user(game_level=1)
        assert user.game_experience_for_next_level() == 300

    def test_game_experience_for_next_level_lv3(self):
        """Lv3 → Lv4 필요 경험치: 900."""
        user = _make_user(game_level=3)
        assert user.game_experience_for_next_level() == 900

    def test_gain_game_experience_no_level_up(self):
        """경험치 획득 후 레벨업 조건 미충족 시 레벨 유지."""
        user = _make_user(game_level=1)
        updated = user.gain_game_experience(100)
        assert updated.game_level == 1
        assert updated.game_experience == 100
        assert updated.game_current_experience == 100

    def test_gain_game_experience_level_up(self):
        """300 XP 획득 → Lv1에서 Lv2로."""
        user = _make_user(game_level=1)
        updated = user.gain_game_experience(300)
        assert updated.game_level == 2
        assert updated.game_experience == 300
        assert updated.game_current_experience == 0  # 딱 맞게 레벨업

    def test_gain_game_experience_partial_after_levelup(self):
        """700 XP: Lv1→Lv2 (300 소비, 잔여 400. Lv2→Lv3은 600 필요이라 미달)."""
        user = _make_user(game_level=1)
        updated = user.gain_game_experience(700)
        assert updated.game_level == 2
        assert updated.game_experience == 700
        assert updated.game_current_experience == 400

    def test_gain_game_experience_accumulates_total(self):
        """game_experience(총합)는 항상 누적된다."""
        user = _make_user(
            game_level=1, game_experience=500, game_current_experience=200
        )
        updated = user.gain_game_experience(50)
        assert updated.game_experience == 550
        assert updated.game_current_experience == 250

    def test_immutability(self):
        """gain_game_experience는 새 인스턴스를 반환한다."""
        user = _make_user(game_level=1)
        updated = user.gain_game_experience(100)
        assert updated is not user
        assert user.game_level == 1  # 원본 불변

    def test_existing_user_level_unchanged(self):
        """기존 user_level(권한 등급)은 변경되지 않는다."""
        user = _make_user()
        updated = user.gain_game_experience(1000)
        assert updated.user_level == UserLevel.NORMAL
