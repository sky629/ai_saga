"""FastAPI Dependency Injection Integration.

FastAPI의 Depends 시스템과 연동하여 Use Case를 라우터에 주입합니다.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.storage.postgres import postgres_storage
from app.game.application.ports import CacheServiceInterface
from app.game.application.queries import (
    GetScenariosQuery,
    GetSessionHistoryQuery,
    GetUserSessionsQuery,
)
from app.game.application.queries.get_characters import GetCharactersQuery
from app.game.application.use_cases import (
    CreateCharacterUseCase,
    GenerateEndingUseCase,
    ProcessActionUseCase,
    StartGameUseCase,
    DeleteSessionUseCase,
)
from app.game.container import GameContainer


async def get_db() -> AsyncSession:
    """DB 세션 의존성."""
    async with postgres_storage.write_db() as db:
        yield db


def get_container(
    db: Annotated[AsyncSession, Depends(postgres_storage.write_db)],
) -> GameContainer:
    """Game Container 의존성 (Write DB)."""
    return GameContainer(db)


def get_read_container(
    db: Annotated[AsyncSession, Depends(postgres_storage.read_db)],
) -> GameContainer:
    """Game Container 의존성 (Read DB)."""
    return GameContainer(db)


# === Use Case Dependencies (Command - Write DB) ===


def get_process_action_use_case(
    container: Annotated[GameContainer, Depends(get_container)],
):
    """ProcessActionUseCase 의존성."""
    return container.process_action_use_case()


def get_start_game_use_case(
    container: Annotated[GameContainer, Depends(get_container)],
):
    """StartGameUseCase 의존성."""
    return container.start_game_use_case()


def get_generate_ending_use_case(
    container: Annotated[GameContainer, Depends(get_container)],
):
    """GenerateEndingUseCase 의존성."""
    return container.generate_ending_use_case()


def get_create_character_use_case(
    container: Annotated[GameContainer, Depends(get_container)],
):
    """CreateCharacterUseCase 의존성."""
    return container.create_character_use_case()


def get_delete_session_use_case(
    container: Annotated[GameContainer, Depends(get_container)],
):
    """DeleteSessionUseCase 의존성."""
    return container.delete_session_use_case()


def get_cache_service(
    container: Annotated[GameContainer, Depends(get_container)],
) -> CacheServiceInterface:
    """CacheService 의존성."""
    return container.cache_service


# === Type Aliases for Route Parameters ===

ProcessActionDep = Annotated[
    ProcessActionUseCase, Depends(get_process_action_use_case)
]
StartGameDep = Annotated[StartGameUseCase, Depends(get_start_game_use_case)]
GenerateEndingDep = Annotated[
    GenerateEndingUseCase, Depends(get_generate_ending_use_case)
]
CreateCharacterDep = Annotated[
    CreateCharacterUseCase, Depends(get_create_character_use_case)
]
DeleteSessionDep = Annotated[
    DeleteSessionUseCase, Depends(get_delete_session_use_case)
]
CacheServiceDep = Annotated[CacheServiceInterface, Depends(get_cache_service)]


# === Query Dependencies (CQRS Read Side - Read DB) ===


def get_scenarios_query(
    container: Annotated[GameContainer, Depends(get_read_container)],
) -> GetScenariosQuery:
    """GetScenariosQuery 의존성."""
    return container.get_scenarios_query()


def get_user_sessions_query(
    container: Annotated[GameContainer, Depends(get_read_container)],
) -> GetUserSessionsQuery:
    """GetUserSessionsQuery 의존성."""
    return container.get_user_sessions_query()


async def get_session_history_query(
    container: Annotated[GameContainer, Depends(get_read_container)],
) -> GetSessionHistoryQuery:
    """GetSessionHistoryQuery 의존성."""
    return await container.get_session_history_query()


def get_characters_query(
    container: Annotated[GameContainer, Depends(get_read_container)],
) -> GetCharactersQuery:
    """GetCharactersQuery 의존성."""
    return container.get_characters_query()


# === Query Type Aliases ===

GetScenariosDep = Annotated[GetScenariosQuery, Depends(get_scenarios_query)]
GetUserSessionsDep = Annotated[
    GetUserSessionsQuery, Depends(get_user_sessions_query)
]
GetSessionHistoryDep = Annotated[
    GetSessionHistoryQuery, Depends(get_session_history_query)
]
GetCharactersDep = Annotated[GetCharactersQuery, Depends(get_characters_query)]
