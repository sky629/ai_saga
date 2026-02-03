"""Auth Repository Interfaces (Ports)."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional
from uuid import UUID

from app.auth.domain.entities import SocialAccountEntity, UserEntity
from app.auth.domain.value_objects import AuthProvider

class UserRepositoryInterface(ABC):
    """사용자 저장소 인터페이스."""

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> Optional[UserEntity]:
        """ID로 사용자 조회."""
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[UserEntity]:
        """이메일로 사용자 조회."""
        pass

    @abstractmethod
    async def save(self, user: UserEntity) -> UserEntity:
        """사용자 저장 (생성/수정)."""
        pass

    @abstractmethod
    async def update_last_login(self, user_id: UUID, login_at: datetime) -> None:
        """마지막 로그인 시간 업데이트."""
        pass


class SocialAccountRepositoryInterface(ABC):
    """소셜 계정 저장소 인터페이스."""

    @abstractmethod
    async def get_by_provider(
        self, provider: AuthProvider, provider_user_id: str
    ) -> Optional[SocialAccountEntity]:
        """Provider ID로 계정 조회."""
        pass

    @abstractmethod
    async def get_by_user(self, user_id: UUID) -> list[SocialAccountEntity]:
        """사용자의 모든 소셜 계정 조회."""
        pass

    @abstractmethod
    async def save(self, account: SocialAccountEntity) -> SocialAccountEntity:
        """소셜 계정 저장."""
        pass
