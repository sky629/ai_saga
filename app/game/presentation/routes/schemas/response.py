"""Game response DTOs - Pydantic models for game API responses."""

from datetime import datetime
from typing import Generic, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

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
    character: "CharacterResponse"


class MessageHistoryResponse(BaseModel):
    """Message history item."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    content: str
    created_at: datetime
    parsed_response: Optional["ParsedResponseModel"] = None
    image_url: Optional[str] = None


class ScenarioResponse(BaseModel):
    """Scenario response model."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str
    game_type: str
    genre: str
    difficulty: str
    max_turns: int
    tags: list[str] = Field(default_factory=list)
    thumbnail_url: Optional[str] = None
    hook: Optional[str] = None
    recommended_for: Optional[str] = None
    world_setting: Optional[str] = None
    initial_location: Optional[str] = None
    is_active: bool = True


class CharacterStatsResponse(BaseModel):
    """Character stats response model."""

    model_config = ConfigDict(from_attributes=True)

    hp: int
    max_hp: int
    level: int


class CharacterProfileResponse(BaseModel):
    """Character profile response model."""

    model_config = ConfigDict(from_attributes=True)

    age: Optional[int] = None
    gender: Optional[str] = None
    appearance: Optional[str] = None
    goal: Optional[str] = None


class CharacterResponse(BaseModel):
    """Character response model."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    scenario_id: UUID
    name: str
    profile: Optional[CharacterProfileResponse] = None
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
    max_turns: int  # 추가: 턴 정보 완성
    ending_type: Optional[str] = None
    started_at: datetime
    last_activity_at: datetime
    image_url: Optional[str] = None  # 초기 삽화 URL
    final_outcome: Optional["FinalOutcomeResponse"] = None


class ProgressionManualResponse(BaseModel):
    """Progression 비급 상태 응답 모델."""

    model_config = ConfigDict(from_attributes=True)

    name: str
    category: str
    mastery: int
    aura: str


class ManualMasteryUpdateResponse(BaseModel):
    """비급 숙련도 변화 응답 모델."""

    model_config = ConfigDict(from_attributes=True)

    name: str
    mastery_delta: int


class StateChangesResponse(BaseModel):
    """게임 상태 변화 응답 모델."""

    model_config = ConfigDict(from_attributes=True)

    hp_change: int = 0
    experience_gained: int = 0
    items_gained: list[str] = Field(default_factory=list)
    items_lost: list[str] = Field(default_factory=list)
    location: Optional[str] = None
    npcs_met: list[str] = Field(default_factory=list)
    discoveries: list[str] = Field(default_factory=list)
    internal_power_delta: int = 0
    external_power_delta: int = 0
    manuals_gained: list[ProgressionManualResponse] = Field(
        default_factory=list
    )
    manual_mastery_updates: list[ManualMasteryUpdateResponse] = Field(
        default_factory=list
    )
    traits_gained: list[str] = Field(default_factory=list)
    title_candidates: list[str] = Field(default_factory=list)


class ProgressionStatusPanelResponse(BaseModel):
    """성장형 상태 패널 응답 모델."""

    model_config = ConfigDict(from_attributes=True)

    hp: int
    max_hp: int
    internal_power: int
    external_power: int
    manuals: list[ProgressionManualResponse] = Field(default_factory=list)
    remaining_turns: int
    elapsed_turns: int
    escape_status: Optional[str] = None


class ProgressionAchievementBoardResponse(BaseModel):
    """성장형 엔딩 업적 보드 응답 모델."""

    model_config = ConfigDict(from_attributes=True)

    character_name: str
    scenario_name: str
    title: str
    escaped: bool
    total_score: int
    hp: int
    max_hp: int
    internal_power: int
    external_power: int
    manuals: list[ProgressionManualResponse] = Field(default_factory=list)
    remaining_turns: int
    traits: list[str] = Field(default_factory=list)
    title_candidates: list[str] = Field(default_factory=list)
    ending_type: Optional[str] = None
    title_reason: str = ""
    summary: str


class FinalOutcomeResponse(BaseModel):
    """세션 완료 시 최종 결과 응답 모델."""

    model_config = ConfigDict(from_attributes=True)

    ending_type: str
    narrative: str
    image_url: Optional[str] = None
    achievement_board: Optional[ProgressionAchievementBoardResponse] = None


class ParsedResponseModel(BaseModel):
    """메시지에 저장되는 구조화 응답 모델."""

    model_config = ConfigDict(from_attributes=True)

    narrative: Optional[str] = None
    before_narrative: Optional[str] = None
    options: list["ActionOptionResponse"] = Field(default_factory=list)
    state_changes: Optional[StateChangesResponse] = None
    status_panel: Optional[ProgressionStatusPanelResponse] = None
    consumes_turn: Optional[bool] = None
    dice_applied: Optional[bool] = None
    image_focus: Optional[str] = None
    ending_type: Optional[str] = None
    final_outcome: Optional[FinalOutcomeResponse] = None


class GameMessageResponse(BaseModel):
    """Game message response model."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    content: str
    parsed_response: Optional[ParsedResponseModel] = None
    image_url: Optional[str] = None
    created_at: datetime


class DiceResultResponse(BaseModel):
    """Dice result response model."""

    model_config = ConfigDict(from_attributes=True)

    roll: int
    modifier: int
    total: int
    dc: int
    is_success: bool
    is_critical: bool
    is_fumble: bool
    check_type: str
    damage: Optional[int] = None
    display_text: str


class ActionOptionResponse(BaseModel):
    """Typed action option response model."""

    model_config = ConfigDict(from_attributes=True)

    label: str
    action_type: str
    requires_dice: bool


class GameActionResponse(BaseModel):
    """Response for a game action."""

    message: GameMessageResponse
    narrative: str
    before_roll_narrative: Optional[str] = None
    options: list[ActionOptionResponse]
    turn_count: int
    max_turns: int
    is_ending: bool = False
    state_changes: Optional[StateChangesResponse] = None
    image_url: Optional[str] = None  # 삽화 이미지 URL
    dice_result: Optional[DiceResultResponse] = None
    status_panel: Optional[ProgressionStatusPanelResponse] = None
    xp_gained: Optional[int] = None
    leveled_up: Optional[bool] = None
    new_game_level: Optional[int] = None


class GameEndingResponse(BaseModel):
    """Response for game ending."""

    session_id: UUID
    ending_type: str  # victory, defeat, neutral
    narrative: str
    total_turns: int
    character_name: str
    scenario_name: str
    is_ending: bool = True
    xp_gained: int = 0
    new_game_level: int = 1
    leveled_up: bool = False
    levels_gained: int = 0
    final_outcome: FinalOutcomeResponse


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


class IllustrationResponse(BaseModel):
    message_id: UUID
    image_url: str


ParsedResponseModel.model_rebuild()
MessageHistoryResponse.model_rebuild()
