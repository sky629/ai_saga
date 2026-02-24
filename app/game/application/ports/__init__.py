"""Repository Interfaces (Ports) for Dependency Inversion.

도메인/애플리케이션 레이어가 인프라에 의존하지 않도록 인터페이스를 정의합니다.
"""

from abc import ABC, abstractmethod
from typing import AsyncContextManager, Optional
from uuid import UUID

from pydantic import BaseModel

from app.game.domain.entities import (
    CharacterEntity,
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
    async def save(self, session: GameSessionEntity) -> GameSessionEntity:
        """세션 저장 (생성 또는 업데이트)."""
        pass

    @abstractmethod
    async def delete(self, session_id: UUID) -> None:
        """세션 삭제."""
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
    async def get_all_active(self) -> list[ScenarioEntity]:
        """모든 활성 시나리오 조회."""
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
    async def get_similar_messages(
        self,
        embedding: list[float],
        session_id: UUID,
        limit: int = 5,
        distance_threshold: float = 0.3,
    ) -> list[GameMessageEntity]:
        """벡터 유사도 기반 메시지 검색.

        Args:
            embedding: 검색 기준 벡터 (768차원)
            session_id: 세션 ID (같은 세션 내에서만 검색)
            limit: 최대 반환 개수
            distance_threshold: 유사도 임계값 (코사인 거리, 낮을수록 유사)

        Returns:
            유사도 높은 순으로 정렬된 메시지 목록
        """
        pass

    @abstractmethod
    async def get_by_id(self, message_id: UUID) -> Optional[GameMessageEntity]:
        pass

    @abstractmethod
    async def update_image_url(
        self, message_id: UUID, image_url: str
    ) -> GameMessageEntity:
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
