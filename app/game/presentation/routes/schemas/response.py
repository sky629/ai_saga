"""Game response DTOs - Pydantic models for game API responses."""

from datetime import datetime
from typing import Generic, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class CursorPaginatedResponse(BaseModel, Generic[T]):
    """Cursor-based pagination response wrapper.

    Optimized for chat/feed-style infinite scroll.
    Uses UUID v7 based cursor.
    """

    items: list[T]
    next_cursor: Optional[UUID] = None
    has_more: bool = False


class SessionListResponse(BaseModel):
    """Game session list item.

    Lightweight response for list endpoint.
    Uses user-friendly names instead of IDs.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    character_name: str
    scenario_name: str
    status: str
    turn_count: int
    max_turns: int
    started_at: datetime
    last_activity_at: datetime
    ending_type: Optional[str] = None


class MessageHistoryResponse(BaseModel):
    """Message history item."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    content: str
    created_at: datetime
    parsed_response: Optional[dict] = None


class ScenarioResponse(BaseModel):
    """Scenario response model."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str
    genre: str
    difficulty: str
    max_turns: int
    world_setting: Optional[str] = None
    initial_location: Optional[str] = None
    is_active: bool = True


class CharacterStatsResponse(BaseModel):
    """Character stats response model."""

    model_config = ConfigDict(from_attributes=True)

    hp: int
    max_hp: int
    level: int


class CharacterResponse(BaseModel):
    """Character response model."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    description: Optional[str]
    stats: CharacterStatsResponse
    inventory: list
    is_active: bool
    created_at: datetime


class GameSessionResponse(BaseModel):
    """Game session response model."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    character_id: UUID
    scenario_id: UUID
    current_location: str
    game_state: dict
    status: str
    turn_count: int
    ending_type: Optional[str] = None
    started_at: datetime
    last_activity_at: datetime


class GameMessageResponse(BaseModel):
    """Game message response model."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    content: str
    parsed_response: Optional[dict] = None
    created_at: datetime


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

    session_id: UUID
    ending_type: str  # victory, defeat, neutral
    narrative: str
    total_turns: int
    character_name: str
    scenario_name: str


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str
