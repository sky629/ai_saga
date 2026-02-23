"""User Progression Domain Service."""

from app.game.domain.value_objects import EndingType, ScenarioDifficulty


class UserProgressionService:
    """유저 메타 프로그레션 계산 서비스.

    순수 계산 로직만 포함. I/O 없음.
    """

    @staticmethod
    def calculate_game_xp(
        ending_type: EndingType,
        turn_count: int,
        difficulty: ScenarioDifficulty,
    ) -> int:
        """게임 결과에 따른 유저 경험치 계산.

        Args:
            ending_type: 게임 엔딩 타입 (VICTORY/DEFEAT/NEUTRAL)
            turn_count: 소비한 턴 수
            difficulty: 시나리오 난이도

        Returns:
            획득 경험치
        """
        base = {
            EndingType.VICTORY: 200,
            EndingType.DEFEAT: 50,
            EndingType.NEUTRAL: 100,
        }[ending_type]
        per_turn = {
            EndingType.VICTORY: 10,
            EndingType.DEFEAT: 5,
            EndingType.NEUTRAL: 7,
        }[ending_type]

        xp = base + (turn_count * per_turn)

        if difficulty in (
            ScenarioDifficulty.HARD,
            ScenarioDifficulty.NIGHTMARE,
        ):
            xp = int(xp * 1.5)

        return xp

    @staticmethod
    def calculate_starting_hp(level: int) -> int:
        """유저 레벨 기반 캐릭터 시작 HP.

        Args:
            level: 유저 게임 레벨

        Returns:
            시작 HP (100 + (level-1) * 10)
        """
        return 100 + (level - 1) * 10
