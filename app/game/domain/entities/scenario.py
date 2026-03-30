"""Scenario Domain Entity."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.game.domain.value_objects import ScenarioDifficulty, ScenarioGenre


class ScenarioEntity(BaseModel):
    """시나리오 도메인 엔티티.

    게임 월드/시나리오 템플릿을 정의합니다.
    관리자에 의해 생성되며, 일반적으로 불변입니다.
    """

    model_config = {"frozen": True}

    id: UUID
    name: str = Field(min_length=1, max_length=200)
    description: str
    world_setting: str
    initial_location: str = Field(max_length=200)
    genre: ScenarioGenre = ScenarioGenre.FANTASY
    difficulty: ScenarioDifficulty = ScenarioDifficulty.NORMAL
    max_turns: int = Field(gt=0, default=30)
    tags: list[str] = Field(default_factory=list)
    thumbnail_url: str | None = None
    hook: str | None = None
    recommended_for: str | None = None
    is_active: bool = True
    created_at: datetime

    # === Domain Methods ===

    def deactivate(self) -> "ScenarioEntity":
        """시나리오 비활성화."""
        return self.model_copy(update={"is_active": False})

    def activate(self) -> "ScenarioEntity":
        """시나리오 활성화."""
        return self.model_copy(update={"is_active": True})

    # === Domain Properties ===

    @property
    def is_playable(self) -> bool:
        """플레이 가능한 시나리오인지 확인."""
        return self.is_active
