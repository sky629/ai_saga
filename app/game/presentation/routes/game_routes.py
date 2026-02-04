"""Game API routes."""

from typing import List, Optional, Union
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Query,
    Response,
    status,
)

from app.auth.dependencies import get_current_user
from app.auth.infrastructure.persistence.models.user_models import User
from app.game.application.use_cases.create_character import (
    CreateCharacterInput,
)
from app.game.application.use_cases.process_action import ProcessActionInput
from app.game.application.use_cases.start_game import StartGameInput
from app.game.dependencies import (
    CacheServiceDep,
    CreateCharacterDep,
    GetCharactersDep,
    GetScenariosDep,
    GetSessionHistoryDep,
    GetUserSessionsDep,
    ProcessActionDep,
    StartGameDep,
)
from app.game.presentation.routes.schemas.request import (
    CreateCharacterRequest,
    GameActionRequest,
    StartGameRequest,
)
from app.game.presentation.routes.schemas.response import (
    CharacterResponse,
    CursorPaginatedResponse,
    GameActionResponse,
    GameEndingResponse,
    GameSessionResponse,
    MessageHistoryResponse,
    ScenarioResponse,
    SessionListResponse,
)

game_router_v1 = APIRouter(
    prefix="/api/v1/game",
    tags=["game"],
)


@game_router_v1.get("/scenarios", response_model=List[ScenarioResponse])
async def list_scenarios(
    query: GetScenariosDep,
    current_user: User = Depends(get_current_user),
):
    """Get all available game scenarios."""
    results = await query.execute()
    return results


@game_router_v1.get("/characters", response_model=List[CharacterResponse])
async def list_characters(
    query: GetCharactersDep,
    current_user: User = Depends(get_current_user),
):
    """Get all characters for current user."""
    characters = await query.execute(current_user.id)
    return characters


@game_router_v1.post(
    "/characters",
    response_model=CharacterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_character(
    request: CreateCharacterRequest,
    use_case: CreateCharacterDep,
    current_user: User = Depends(get_current_user),
):
    """Create a new character."""
    input_data = CreateCharacterInput(
        name=request.name, description=request.description
    )
    character = await use_case.execute(current_user.id, input_data)
    return character


@game_router_v1.get(
    "/sessions", response_model=CursorPaginatedResponse[SessionListResponse]
)
async def list_sessions(
    query: GetUserSessionsDep,
    current_user: User = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100, description="Page size"),
    cursor: Optional[UUID] = Query(None, description="Next page cursor"),
    status: Optional[str] = Query(
        None, pattern="^(active|completed|abandoned)$"
    ),
):
    """Get game sessions list (Cursor-based pagination)."""
    sessions = await query.execute(
        user_id=current_user.id,
        status_filter=status,
        limit=limit,
        cursor=cursor,
    )

    # has_more check
    has_more = len(sessions) > limit
    if has_more:
        sessions = sessions[:limit]

    # next_cursor calculation
    next_cursor = sessions[-1].id if sessions and has_more else None

    return CursorPaginatedResponse(
        items=sessions,
        next_cursor=next_cursor,
        has_more=has_more,
    )


@game_router_v1.post(
    "/sessions",
    response_model=GameSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_game(
    request: StartGameRequest,
    use_case: StartGameDep,
    current_user: User = Depends(get_current_user),
):
    """Start a new game session."""
    input_data = StartGameInput(
        character_id=request.character_id,
        scenario_id=request.scenario_id,
        max_turns=request.max_turns,
    )
    result = await use_case.execute(current_user.id, input_data)
    return result


@game_router_v1.post(
    "/sessions/{session_id}/actions",
    response_model=Union[GameActionResponse, GameEndingResponse],
)
async def submit_action(
    session_id: UUID,
    request: GameActionRequest,
    use_case: ProcessActionDep,
    cache_service: CacheServiceDep,
    response: Response,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
):
    """Submit a player action to a game session."""
    input_data = ProcessActionInput(
        session_id=session_id,
        action=request.action,
        idempotency_key=idempotency_key,
    )

    # Endpoint-level Distributed Lock
    lock_key = f"game:{session_id}:{idempotency_key}"
    async with cache_service.lock(lock_key, ttl_ms=20000):  # 20s lock
        result = await use_case.execute(current_user.id, input_data)

    if result.is_cached:
        response.headers["X-Is-Idempotent"] = "true"

    return result.response


@game_router_v1.get(
    "/sessions/{session_id}/messages",
    response_model=CursorPaginatedResponse[MessageHistoryResponse],
)
async def get_session_messages(
    session_id: UUID,
    query: GetSessionHistoryDep,
    current_user: User = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=100, description="Message count"),
    cursor: Optional[UUID] = Query(None, description="Next page cursor"),
):
    """Get session message history (Cursor-based pagination).

    Returns latest messages first. Supports infinity scroll.
    """
    messages, next_cursor, has_more = await query.execute_with_cursor(
        session_id=session_id,
        limit=limit,
        cursor=cursor,
    )

    if not messages and not cursor:
        # Session itself doesn't exist
        raise HTTPException(status_code=404, detail="Session not found")

    return CursorPaginatedResponse(
        items=messages,
        next_cursor=next_cursor,
        has_more=has_more,
    )
