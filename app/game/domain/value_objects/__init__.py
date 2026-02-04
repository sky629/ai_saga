"""Game Domain Value Objects - Enums for type safety."""

from .ending_type import EndingType
from .message_role import MessageRole
from .scenario_difficulty import ScenarioDifficulty
from .scenario_genre import ScenarioGenre
from .session_status import SessionStatus

__all__ = [
    "SessionStatus",
    "EndingType",
    "MessageRole",
    "ScenarioDifficulty",
    "ScenarioGenre",
]
