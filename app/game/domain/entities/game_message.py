"""GameMessage Domain Entity."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.game.domain.value_objects import MessageRole


class GameMessageEntity(BaseModel):
    """게임 메시지 도메인 엔티티.
    
    게임 세션 내의 개별 메시지(플레이어 액션 또는 AI 응답)를 표현합니다.
    """
    model_config = {"frozen": True}

    id: UUID
    session_id: UUID
    role: MessageRole
    content: str = Field(min_length=1)
    parsed_response: Optional[dict] = None
    token_count: Optional[int] = Field(ge=0, default=None)
    created_at: datetime

    # === Domain Methods ===

    def with_parsed_response(self, parsed: dict) -> "GameMessageEntity":
        """파싱된 응답을 추가한 새 인스턴스 반환."""
        return self.model_copy(update={"parsed_response": parsed})

    # === Domain Properties ===

    @property
    def is_player_message(self) -> bool:
        """플레이어 메시지인지 확인."""
        return self.role == MessageRole.USER

    @property
    def is_ai_response(self) -> bool:
        """AI 응답인지 확인."""
        return self.role == MessageRole.ASSISTANT

    @property
    def summary(self) -> str:
        """메시지 요약 (처음 100자)."""
        return self.content[:100] + "..." if len(self.content) > 100 else self.content
