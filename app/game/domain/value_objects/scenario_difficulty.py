from enum import Enum


class ScenarioDifficulty(str, Enum):
    """Difficulty levels for game scenarios."""

    EASY = "easy"
    NORMAL = "normal"
    HARD = "hard"
    NIGHTMARE = "nightmare"
