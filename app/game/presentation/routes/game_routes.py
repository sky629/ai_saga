"""Game API routes."""

import hashlib
import json
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
from sqlalchemy.exc import IntegrityError

from app.auth.dependencies import get_current_user
from app.auth.infrastructure.persistence.models.user_models import User
from app.common.exception import APIException, Conflict
from app.game.application.use_cases.create_character import (
    CreateCharacterInput,
)
from app.game.application.use_cases.generate_illustration import (
    GenerateIllustrationInput,
)
from app.game.application.use_cases.process_action import ProcessActionInput
from app.game.application.use_cases.start_game import StartGameInput
from app.game.dependencies import (
    CacheServiceDep,
    CreateCharacterDep,
    DeleteSessionDep,
    GenerateIllustrationDep,
    GetCharactersDep,
    GetScenariosDep,
    GetSessionDep,
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
    IllustrationResponse,
    MessageHistoryResponse,
    ScenarioResponse,
    SessionListResponse,
)

game_router_v1 = APIRouter(
    prefix="/api/v1/game",
    tags=["game"],
)


@game_router_v1.get("/scenarios/", response_model=List[ScenarioResponse])
async def list_scenarios(
    query: GetScenariosDep,
    current_user: User = Depends(get_current_user),
):
    """Get all available game scenarios."""
    results = await query.execute()
    return results


@game_router_v1.get("/characters/", response_model=List[CharacterResponse])
async def list_characters(
    query: GetCharactersDep,
    current_user: User = Depends(get_current_user),
):
    """Get all characters for current user."""
    characters = await query.execute(current_user.id)
    return characters


@game_router_v1.post(
    "/characters/",
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
        name=request.name,
        scenario_id=request.scenario_id,
        profile=request.profile.model_dump(exclude_none=True),
    )
    try:
        character = await use_case.execute(current_user.id, input_data)
    except ValueError as e:
        error_msg = str(e).lower()
        if "scenario not found" in error_msg or "inactive" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scenario not found",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    return character


@game_router_v1.get(
    "/sessions/", response_model=CursorPaginatedResponse[SessionListResponse]
)
async def list_sessions(
    query: GetUserSessionsDep,
    current_user: User = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100, description="Page size"),
    cursor: Optional[UUID] = Query(None, description="Next page cursor"),
    status: Optional[str] = Query(
        None, pattern="^(active|paused|completed|ended)$"
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
    "/sessions/",
    response_model=GameSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_game(
    request: StartGameRequest,
    use_case: StartGameDep,
    cache_service: CacheServiceDep,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
):
    """Start a new game session.

    Supports idempotency via `Idempotency-Key` header.
    Prevents concurrent session creation for the same user/key.
    """
    input_data = StartGameInput(
        character_id=request.character_id,
        scenario_id=request.scenario_id,
        max_turns=request.max_turns,
    )
    lock_key = f"game:start:character:{request.character_id}"

    if idempotency_key:
        payload = {
            "character_id": str(request.character_id),
            "scenario_id": str(request.scenario_id),
            "max_turns": request.max_turns,
        }
        payload_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode("utf-8")
        ).hexdigest()
        replay_key = (
            f"game:start:idempotency:{current_user.id}:{idempotency_key}"
        )
        cached_payload = await cache_service.get(replay_key)
        if cached_payload:
            replay_data = json.loads(cached_payload)
            if replay_data.get("payload_hash") != payload_hash:
                raise Conflict(
                    message=(
                        "같은 Idempotency-Key에 다른 요청 본문을 사용할 수 없습니다."
                    )
                )
            return GameSessionResponse.model_validate(replay_data["response"])

        async with cache_service.lock(lock_key, ttl_ms=20000):
            cached_payload = await cache_service.get(replay_key)
            if cached_payload:
                replay_data = json.loads(cached_payload)
                if replay_data.get("payload_hash") != payload_hash:
                    raise Conflict(
                        message=(
                            "같은 Idempotency-Key에 다른 요청 본문을 사용할 수 없습니다."
                        )
                    )
                return GameSessionResponse.model_validate(
                    replay_data["response"]
                )

            try:
                result = await use_case.execute(current_user.id, input_data)
            except ValueError as e:
                error_msg = str(e).lower()
                if "active session" in error_msg:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Character already has an active session",
                    )
                if "not found" in error_msg:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=str(e),
                    )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e),
                )
            except IntegrityError:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Character already has an active session",
                )
            await cache_service.set(
                replay_key,
                json.dumps(
                    {
                        "payload_hash": payload_hash,
                        "response": result.model_dump(mode="json"),
                    }
                ),
                ttl_seconds=600,
            )
    else:
        # No idempotency key, just execute
        async with cache_service.lock(lock_key, ttl_ms=20000):
            try:
                result = await use_case.execute(current_user.id, input_data)
            except ValueError as e:
                error_msg = str(e).lower()
                if "active session" in error_msg:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Character already has an active session",
                    )
                if "not found" in error_msg:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=str(e),
                    )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e),
                )
            except IntegrityError:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Character already has an active session",
                )

    return result


@game_router_v1.get(
    "/sessions/{session_id}/",
    response_model=GameSessionResponse,
)
async def get_session(
    session_id: UUID,
    query: GetSessionDep,
    current_user: User = Depends(get_current_user),
):
    """게임 세션 단건 조회.

    세션의 상세 정보를 조회합니다. game_state를 포함한 모든 정보를 반환합니다.
    자신이 소유한 세션만 조회 가능합니다.
    """
    session = await query.execute(session_id, current_user.id)

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    # game_state 정리: 채팅창에 이미 표시되는 정보 제거
    cleaned_game_state = {
        k: v
        for k, v in session.game_state.items()
        if k not in ["discoveries", "visited_locations"]
    }

    # 응답 생성 (game_state만 정리)
    return GameSessionResponse(
        id=session.id,
        character_id=session.character_id,
        scenario_id=session.scenario_id,
        current_location=session.current_location,
        game_state=cleaned_game_state,
        status=session.status.value,
        turn_count=session.turn_count,
        max_turns=session.max_turns,
        ending_type=session.ending_type.value if session.ending_type else None,
        started_at=session.started_at,
        last_activity_at=session.last_activity_at,
    )


@game_router_v1.delete(
    "/sessions/{session_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_session(
    session_id: UUID,
    use_case: DeleteSessionDep,
    current_user: User = Depends(get_current_user),
):
    """Delete a game session."""
    try:
        await use_case.execute(current_user.id, session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )


@game_router_v1.post(
    "/sessions/{session_id}/actions/",
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
    if not idempotency_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Idempotency-Key header is required",
        )

    input_data = ProcessActionInput(
        session_id=session_id,
        action=request.action,
        action_type=request.action_type,
        idempotency_key=idempotency_key,
    )

    # Endpoint-level Distributed Lock
    lock_key = f"game:action:{session_id}"
    async with cache_service.lock(lock_key, ttl_ms=20000):  # 20s lock
        try:
            result = await use_case.execute(current_user.id, input_data)
        except ValueError as e:
            error_msg = str(e)
            if "completed" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Session is already completed. Cannot process further actions.",
                )
            elif (
                "not active" in error_msg.lower()
                or "not in active state" in error_msg.lower()
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=error_msg,
                )
            elif "does not belong to user" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Session does not belong to current user",
                )
            elif "not found" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Session not found",
                )
            # 다른 ValueError는 그대로 re-raise
            raise

    if result.is_cached:
        response.headers["X-Is-Idempotent"] = "true"

    return result.response


@game_router_v1.get(
    "/sessions/{session_id}/messages/",
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
        user_id=current_user.id,
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


@game_router_v1.post(
    "/sessions/{session_id}/messages/{message_id}/illustration/",
    response_model=IllustrationResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_illustration(
    session_id: UUID,
    message_id: UUID,
    use_case: GenerateIllustrationDep,
    cache_service: CacheServiceDep,
    current_user: User = Depends(get_current_user),
):
    async with cache_service.lock(
        f"game:illustration:{message_id}", ttl_ms=20000
    ):
        try:
            result = await use_case.execute(
                current_user.id,
                GenerateIllustrationInput(
                    session_id=session_id,
                    message_id=message_id,
                ),
            )
        except APIException:
            raise
    return IllustrationResponse(
        message_id=result.message_id,
        image_url=result.image_url,
    )
