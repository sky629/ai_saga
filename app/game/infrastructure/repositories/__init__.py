"""Repository Implementations - Adapters for Infrastructure.

Port 인터페이스를 구현하여 실제 인프라(DB, Redis 등)와 연결합니다.
"""

from .game_session_repository import GameSessionRepositoryImpl
from .character_repository import CharacterRepositoryImpl
from .scenario_repository import ScenarioRepositoryImpl
from .game_message_repository import GameMessageRepositoryImpl

__all__ = [
    "GameSessionRepositoryImpl",
    "CharacterRepositoryImpl",
    "ScenarioRepositoryImpl",
    "GameMessageRepositoryImpl",
]
