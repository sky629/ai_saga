"""Game request DTOs - Pydantic models for game API requests."""

from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CharacterProfileRequest(BaseModel):
    """캐릭터 온보딩 프로필 요청."""

    age: int = Field(..., ge=0)
    gender: Literal["남성", "여성", "비공개"]
    appearance: str = Field(..., min_length=1, max_length=300)
    goal: Optional[str] = Field(None, max_length=300)


class CreateCharacterRequest(BaseModel):
    """Request to create a new character."""

    name: str = Field(..., min_length=1, max_length=100)
    scenario_id: UUID
    profile: CharacterProfileRequest


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
    action_type: Optional[str] = Field(
        None, description="선택지 클릭 등으로 전달된 액션 타입"
    )
