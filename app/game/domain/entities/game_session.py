"""GameSession Domain Entity."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.common.utils.datetime import get_utc_datetime
from app.game.domain.value_objects import EndingType, SessionStatus


class GameSessionEntity(BaseModel):
    """게임 세션 도메인 엔티티.

    불변(frozen) 모델로, 상태 변경 시 새 인스턴스를 반환합니다.
    ORM 모델과 분리되어 순수 비즈니스 로직만 포함합니다.
    """

    model_config = {"frozen": True}

    id: UUID
    character_id: UUID
    scenario_id: UUID
    current_location: str
    game_state: dict = Field(default_factory=dict)
    status: SessionStatus = SessionStatus.ACTIVE
    turn_count: int = Field(ge=0, default=0)
    max_turns: int = Field(gt=0, default=30)
    ending_type: Optional[EndingType] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    last_activity_at: datetime

    # === Domain Methods ===

    def advance_turn(self) -> "GameSessionEntity":
        """턴을 1 증가시킨 새 인스턴스 반환."""
        if not self.is_active:
            raise ValueError("Cannot advance turn on inactive session")
        return self.model_copy(
            update={
                "turn_count": self.turn_count + 1,
                "last_activity_at": get_utc_datetime(),
            }
        )

    def complete(self, ending: EndingType) -> "GameSessionEntity":
        """게임을 완료 상태로 변경."""
        return self.model_copy(
            update={
                "status": SessionStatus.COMPLETED,
                "ending_type": ending,
                "ended_at": get_utc_datetime(),
            }
        )

    def pause(self) -> "GameSessionEntity":
        """게임을 일시정지 상태로 변경."""
        if not self.is_active:
            raise ValueError("Cannot pause inactive session")
        return self.model_copy(update={"status": SessionStatus.PAUSED})

    def resume(self) -> "GameSessionEntity":
        """일시정지된 게임을 재개."""
        if self.status != SessionStatus.PAUSED:
            raise ValueError("Can only resume paused session")
        return self.model_copy(
            update={
                "status": SessionStatus.ACTIVE,
                "last_activity_at": get_utc_datetime(),
            }
        )

    def update_location(self, new_location: str) -> "GameSessionEntity":
        """현재 위치 업데이트."""
        return self.model_copy(update={"current_location": new_location})

    # === Domain Properties ===

    @property
    def is_active(self) -> bool:
        """활성 상태인지 확인."""
        return self.status == SessionStatus.ACTIVE

    @property
    def is_final_turn(self) -> bool:
        """마지막 턴인지 확인."""
        return self.turn_count >= self.max_turns

    @property
    def remaining_turns(self) -> int:
        """남은 턴 수."""
        return max(0, self.max_turns - self.turn_count)
