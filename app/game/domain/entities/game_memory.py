"""검색용 게임 메모리 도메인 엔티티."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.game.domain.value_objects import GameMemoryType, MessageRole


class GameMemoryEntity(BaseModel):
    """RAG 검색과 회상을 위한 정규화 메모리 엔티티."""

    model_config = {"frozen": True}

    id: UUID
    session_id: UUID
    source_message_id: Optional[UUID] = None
    role: MessageRole
    memory_type: GameMemoryType
    content: str = Field(min_length=1)
    parsed_response: Optional[dict] = None
    embedding: list[float]
    similarity_distance: Optional[float] = None
    created_at: datetime

    @property
    def is_player_message(self) -> bool:
        """플레이어 기원 메모리인지 확인."""
        return self.role == MessageRole.USER

    @property
    def is_ai_response(self) -> bool:
        """AI 기원 메모리인지 확인."""
        return self.role == MessageRole.ASSISTANT
