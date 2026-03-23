"""Game Domain Value Objects - Enums for type safety."""

from .action_type import ActionType
from .dice import DiceCheckType, DiceResult
from .ending_type import EndingType
from .game_memory_type import GameMemoryType
from .game_state import GameState, StateChanges
from .message_role import MessageRole
from .scenario_difficulty import ScenarioDifficulty
from .scenario_genre import ScenarioGenre
from .session_status import SessionStatus

__all__ = [
    "SessionStatus",
    "ActionType",
    "EndingType",
    "GameMemoryType",
    "MessageRole",
    "ScenarioDifficulty",
    "ScenarioGenre",
    "GameState",
    "StateChanges",
    "DiceCheckType",
    "DiceResult",
]
