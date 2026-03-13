from enum import Enum


class ScenarioDifficulty(str, Enum):
    """Difficulty levels for game scenarios."""

    EASY = "easy"
    NORMAL = "normal"
    HARD = "hard"
    NIGHTMARE = "nightmare"

    @property
    def dc(self) -> int:
        """난이도별 기본 DC."""
        dc_map = {
            ScenarioDifficulty.EASY: 10,
            ScenarioDifficulty.NORMAL: 13,
            ScenarioDifficulty.HARD: 16,
            ScenarioDifficulty.NIGHTMARE: 19,
        }
        return dc_map[self]
