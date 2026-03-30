"""Repository Interfaces (Ports) for Dependency Inversion.

도메인/애플리케이션 레이어가 인프라에 의존하지 않도록 인터페이스를 정의합니다.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import AsyncContextManager, Optional
from uuid import UUID

from pydantic import BaseModel

from app.game.domain.entities import (
    CharacterEntity,
    GameMemoryEntity,
    GameMessageEntity,
    GameSessionEntity,
    ScenarioEntity,
)
from app.llm.dto.llm_response import LLMResponse


class GameSessionRepositoryInterface(ABC):
    """게임 세션 저장소 인터페이스."""

    @abstractmethod
    async def get_by_id(self, session_id: UUID) -> Optional[GameSessionEntity]:
        """ID로 세션 조회."""
        pass

    @abstractmethod
    async def get_active_by_character(
        self, character_id: UUID
    ) -> Optional[GameSessionEntity]:
        """캐릭터의 활성 세션 조회."""
        pass

    @abstractmethod
    async def list_by_user(
        self,
        user_id: UUID,
        status_filter: Optional[str] = None,
        limit: int = 20,
        cursor: Optional[UUID] = None,
    ) -> list["UserSessionReadModel"]:
        """사용자 세션 목록 조회."""
        pass

    @abstractmethod
    async def save(self, session: GameSessionEntity) -> GameSessionEntity:
        """세션 저장 (생성 또는 업데이트)."""
        pass

    @abstractmethod
    async def delete(self, session_id: UUID) -> None:
        """세션 삭제."""
        pass

    @abstractmethod
    async def commit(self) -> None:
        """세션 관련 트랜잭션 커밋."""
        pass


class CharacterRepositoryInterface(ABC):
    """캐릭터 저장소 인터페이스."""

    @abstractmethod
    async def get_by_id(self, character_id: UUID) -> Optional[CharacterEntity]:
        """ID로 캐릭터 조회."""
        pass

    @abstractmethod
    async def get_by_user(self, user_id: UUID) -> list[CharacterEntity]:
        """사용자의 모든 캐릭터 조회."""
        pass

    @abstractmethod
    async def save(self, character: CharacterEntity) -> CharacterEntity:
        """캐릭터 저장."""
        pass

    @abstractmethod
    async def delete(self, character_id: UUID) -> None:
        """캐릭터 삭제."""
        pass


class ScenarioRepositoryInterface(ABC):
    """시나리오 저장소 인터페이스."""

    @abstractmethod
    async def get_by_id(self, scenario_id: UUID) -> Optional[ScenarioEntity]:
        """ID로 시나리오 조회."""
        pass

    @abstractmethod
    async def get_all(self, active_only: bool = True) -> list[ScenarioEntity]:
        """시나리오 목록 조회."""
        pass


class GameMessageRepositoryInterface(ABC):
    """게임 메시지 저장소 인터페이스."""

    @abstractmethod
    async def create(self, message: GameMessageEntity) -> GameMessageEntity:
        """메시지 생성."""
        pass

    @abstractmethod
    async def get_recent_messages(
        self, session_id: UUID, limit: int = 20
    ) -> list[GameMessageEntity]:
        """최근 메시지 조회."""
        pass

    @abstractmethod
    async def get_messages(
        self,
        session_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[GameMessageEntity]:
        """세션 메시지 조회."""
        pass

    @abstractmethod
    async def get_messages_with_cursor(
        self,
        session_id: UUID,
        limit: int = 50,
        cursor: Optional[UUID] = None,
    ) -> tuple[list[GameMessageEntity], Optional[UUID], bool]:
        """Cursor 기반 세션 메시지 조회."""
        pass

    @abstractmethod
    async def get_by_id(self, message_id: UUID) -> Optional[GameMessageEntity]:
        pass

    @abstractmethod
    async def get_first_illustrated_message(
        self, session_id: UUID
    ) -> Optional[GameMessageEntity]:
        """세션의 첫 삽화 메시지 조회."""
        pass

    @abstractmethod
    async def update_image_url(
        self, message_id: UUID, image_url: str
    ) -> GameMessageEntity:
        pass


class GameMemoryRepositoryInterface(ABC):
    """게임 검색 메모리 저장소 인터페이스."""

    @abstractmethod
    async def create(self, memory: GameMemoryEntity) -> GameMemoryEntity:
        """검색용 메모리 생성."""
        pass

    @abstractmethod
    async def get_similar_memories(
        self,
        embedding: list[float],
        session_id: UUID,
        limit: int = 5,
        distance_threshold: float = 0.3,
        exclude_memory_ids: Optional[list[UUID]] = None,
    ) -> list[GameMemoryEntity]:
        """벡터 유사도 기반 메모리 검색."""
        pass


class LLMServiceInterface(ABC):
    """LLM 서비스 인터페이스."""

    @abstractmethod
    async def generate_response(
        self,
        system_prompt: str,
        messages: list[dict],
        temperature: float = 0.8,
    ) -> LLMResponse:
        """LLM 응답 생성."""
        pass


class CacheServiceInterface(ABC):
    """캐시 서비스 인터페이스 (멱등성 등)."""

    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
        """캐시 조회."""
        pass

    @abstractmethod
    async def set(self, key: str, value: str, ttl_seconds: int = 600) -> None:
        """캐시 저장."""
        pass

    @abstractmethod
    def lock(self, key: str, ttl_ms: int = 1000) -> AsyncContextManager:
        """분산 락 (Redis Lock) 컨텍스트 매니저 반환."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        """캐시 삭제."""
        pass


class ImageGenerationServiceInterface(ABC):
    """이미지 생성 서비스 인터페이스."""

    @abstractmethod
    async def generate_image(
        self,
        prompt: str,
        session_id: str,
        user_id: str,
    ) -> Optional[str]:
        """이미지 생성 후 URL 반환.

        Args:
            prompt: 이미지 생성 프롬프트
            session_id: 세션 ID (저장 경로용)
            user_id: 사용자 ID (저장 경로용)

        Returns:
            생성된 이미지의 공개 URL, 실패 시 None
        """
        pass

    @abstractmethod
    async def delete_image(self, image_url: str) -> None:
        """업로드된 이미지를 삭제한다."""
        pass


@dataclass(frozen=True)
class UserSessionReadModel:
    """사용자 세션 목록 조회 모델."""

    id: UUID
    character_name: str
    scenario_name: str
    status: str
    turn_count: int
    max_turns: int
    started_at: datetime
    last_activity_at: datetime
    ending_type: Optional[str]
    character: CharacterEntity


class UserProgressionResult(BaseModel):
    """유저 게임 레벨 진행 결과."""

    model_config = {"frozen": True}

    game_level: int
    game_experience: int
    game_current_experience: int
    leveled_up: bool
    levels_gained: int


class UserProgressionInterface(ABC):
    """유저 게임 진행도 저장소 인터페이스."""

    @abstractmethod
    async def get_user_game_level(self, user_id: UUID) -> int:
        """유저의 현재 게임 레벨 조회."""
        pass

    @abstractmethod
    async def award_game_experience(
        self, user_id: UUID, xp: int
    ) -> UserProgressionResult:
        """유저에게 게임 경험치 부여 후 결과 반환."""
        pass
