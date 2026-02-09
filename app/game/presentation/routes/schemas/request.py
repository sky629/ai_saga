"""Game request DTOs - Pydantic models for game API requests."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CreateCharacterRequest(BaseModel):
    """Request to create a new character."""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    scenario_id: UUID


class StartGameRequest(BaseModel):
    """Request to start a new game session."""

    character_id: UUID
    scenario_id: UUID
    max_turns: Optional[int] = Field(
        None,
        ge=1,
        le=100,
        description="Max turns for this session (1-100, default: from settings)",
    )


class GameActionRequest(BaseModel):
    """Request for a player action in the game."""

    action: str = Field(..., min_length=1, max_length=1000)
