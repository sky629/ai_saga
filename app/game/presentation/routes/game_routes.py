"""Game API routes."""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.infrastructure.persistence.models.postgres_models import User
from app.auth.services.token_service import get_current_user
from app.game.application.use_cases.create_character import CreateCharacterInput
from app.game.application.use_cases.start_game import StartGameInput
from app.game.application.use_cases.process_action import ProcessActionInput
from app.game.dependencies import (
    GetScenariosDep,
    GetCharactersDep,
    CreateCharacterDep,
    GetUserSessionsDep,
    StartGameDep,
    ProcessActionDep,
    GetSessionHistoryDep,
    GenerateEndingDep,
)
from app.game.presentation.routes.schemas.request import (
    CreateCharacterRequest,
    GameActionRequest,
    StartGameRequest,
)
from app.game.presentation.routes.schemas.response import (
    CharacterResponse,
    GameActionResponse,
    GameEndingResponse,
    GameSessionResponse,
    MessageResponse,
    ScenarioResponse,
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

@game_router_v1.post("/characters", response_model=CharacterResponse, status_code=status.HTTP_201_CREATED)
async def create_character(
    request: CreateCharacterRequest,
    use_case: CreateCharacterDep,
    current_user: User = Depends(get_current_user),
):
    """Create a new character."""
    input_data = CreateCharacterInput(name=request.name, description=request.description)
    character = await use_case.execute(current_user.id, input_data)
    return character

@game_router_v1.get("/sessions", response_model=List[GameSessionResponse])
async def list_sessions(
    query: GetUserSessionsDep,
    current_user: User = Depends(get_current_user),
):
    """Get all game sessions for current user."""
    sessions = await query.execute(current_user.id)
    return sessions

@game_router_v1.post("/sessions", response_model=GameSessionResponse, status_code=status.HTTP_201_CREATED)
async def start_game(
    request: StartGameRequest,
    use_case: StartGameDep,
    current_user: User = Depends(get_current_user),
):
    """Start a new game session."""
    input_data = StartGameInput(
        character_id=uuid.UUID(request.character_id),
        scenario_id=uuid.UUID(request.scenario_id),
        max_turns=request.max_turns
    )
    result = await use_case.execute(current_user.id, input_data)
    return result

@game_router_v1.post("/sessions/{session_id}/actions", response_model=GameActionResponse)
async def submit_action(
    session_id: uuid.UUID,
    request: GameActionRequest,
    use_case: ProcessActionDep,
    current_user: User = Depends(get_current_user),
):
    """Submit a player action to a game session."""
    input_data = ProcessActionInput(
        session_id=session_id,
        action=request.action
    )
    result = await use_case.execute(input_data)
    return result

@game_router_v1.get("/sessions/{session_id}/history", response_model=dict)
async def get_history(
    session_id: uuid.UUID,
    query: GetSessionHistoryDep,
    current_user: User = Depends(get_current_user),
):
    """Get message history for a session."""
    history = await query.execute(session_id)
    if not history:
        raise HTTPException(status_code=404, detail="Session not found")
    return history
