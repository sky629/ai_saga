"""Game response DTOs - Pydantic models for game API responses."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ScenarioResponse(BaseModel):
    """Scenario response model."""

    id: uuid.UUID
    name: str
    description: str
    world_setting: str
    initial_location: str
    max_turns: int
    is_active: bool

    class Config:
        from_attributes = True


class CharacterResponse(BaseModel):
    """Character response model."""

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    description: Optional[str]
    stats: dict
    inventory: list
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class GameSessionResponse(BaseModel):
    """Game session response model."""

    id: uuid.UUID
    character_id: uuid.UUID
    scenario_id: uuid.UUID
    current_location: str
    game_state: dict
    status: str
    turn_count: int
    ending_type: Optional[str] = None
    started_at: datetime
    last_activity_at: datetime

    class Config:
        from_attributes = True


class GameMessageResponse(BaseModel):
    """Game message response model."""

    id: uuid.UUID
    role: str
    content: str
    parsed_response: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True


class GameActionResponse(BaseModel):
    """Response for a game action."""

    message: GameMessageResponse
    narrative: str
    options: list[str]
    turn_count: int
    max_turns: int
    is_ending: bool = False
    state_changes: Optional[dict] = None


class GameEndingResponse(BaseModel):
    """Response for game ending."""

    session_id: uuid.UUID
    ending_type: str  # victory, defeat, neutral
    narrative: str
    total_turns: int
    character_name: str
    scenario_name: str


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str

