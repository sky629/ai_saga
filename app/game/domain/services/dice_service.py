"""Dice Domain Service.

주사위 굴림 및 TRPG 판정 로직을 처리하는 순수 도메인 서비스.
외부 의존성 없이 게임 규칙을 처리합니다.
"""

import random

from app.game.domain.value_objects import ScenarioDifficulty
from app.game.domain.value_objects.dice import DiceCheckType, DiceResult


class DiceService:
    """주사위 서비스.

    d20 주사위 판정, 수정치 계산, 데미지 롤 등 TRPG 규칙을 처리합니다.
    모든 메서드는 @staticmethod로 순수 함수로 구현됩니다.
    """

    @staticmethod
    def roll_d20() -> int:
        """1d20 주사위를 굴립니다.

        Returns:
            1에서 20 사이의 무작위 정수
        """
        return random.randint(1, 20)

    @staticmethod
    def calculate_modifier(level: int) -> int:
        """캐릭터 레벨 기반 수정치를 계산합니다.

        D&D 5e 숙련 별너스 공식: (level-1)//4 + 2
        Lv1-4: +2, Lv5-8: +3, Lv9-12: +4, ...

        Args:
            level: 캐릭터 레벨 (1 이상)

        Returns:
            주사위 판정에 적용할 수정치
        """
        return (level - 1) // 4 + 2

    @staticmethod
    def get_dc(difficulty: ScenarioDifficulty) -> int:
        """시나리오 난이도에 따른 DC(Difficulty Class)를 반환합니다.

        Args:
            difficulty: 시나리오 난이도

        Returns:
            목표 주사위 값 (DC)
        """
        dc_map = {
            ScenarioDifficulty.EASY: 8,
            ScenarioDifficulty.NORMAL: 12,
            ScenarioDifficulty.HARD: 15,
            ScenarioDifficulty.NIGHTMARE: 18,
        }
        return dc_map.get(difficulty, 12)

    @staticmethod
    def get_damage_dice(level: int) -> tuple[int, int]:
        """레벨에 따른 데미지 주사위 (개수, 면수)를 반환합니다.

        Args:
            level: 캐릭터 레벨

        Returns:
            (주사위 개수, 주사위 면수) 튜플
        """
        if level <= 2:
            return (1, 4)
        elif level <= 4:
            return (1, 6)
        elif level <= 6:
            return (1, 8)
        elif level <= 8:
            return (1, 10)
        else:
            return (1, 12)

    @staticmethod
    def roll_damage(level: int, is_critical: bool = False) -> int:
        """데미지 주사위를 굴립니다.

        Args:
            level: 캐릭터 레벨
            is_critical: 크리티컬 히트 여부 (True면 주사위 2배)

        Returns:
            데미지 값
        """
        count, sides = DiceService.get_damage_dice(level)
        if is_critical:
            count *= 2
        return sum(random.randint(1, sides) for _ in range(count))

    @staticmethod
    def roll_fumble_damage() -> int:
        """펌블(대실패) 시 자해 데미지를 굴립니다.

        Returns:
            1d4 데미지 값
        """
        return random.randint(1, 4)

    @staticmethod
    def perform_check(
        level: int,
        difficulty: ScenarioDifficulty,
        check_type: DiceCheckType,
    ) -> DiceResult:
        """완전한 주사위 판정을 수행합니다.

        Args:
            level: 캐릭터 레벨
            difficulty: 시나리오 난이도
            check_type: 주사위 체크 유형

        Returns:
            DiceResult: 판정 결과
        """
        roll = DiceService.roll_d20()
        modifier = DiceService.calculate_modifier(level)
        dc = DiceService.get_dc(difficulty)

        is_critical = roll == 20
        is_fumble = roll == 1
        damage = None
        if is_critical:
            damage = DiceService.roll_damage(level, is_critical=True)
        elif is_fumble:
            damage = DiceService.roll_fumble_damage()

        return DiceResult(
            roll=roll,
            modifier=modifier,
            dc=dc,
            check_type=check_type,
            damage=damage,
        )
