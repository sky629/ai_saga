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
    async def update_last_login(
        self, user_id: UUID, login_at: datetime
    ) -> None:
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
    async def get_by_id(
        self, account_id: UUID
    ) -> Optional[SocialAccountEntity]:
        """ID로 소셜 계정 조회."""
        pass

    @abstractmethod
    async def save(self, account: SocialAccountEntity) -> SocialAccountEntity:
        """소셜 계정 저장."""
        pass

    @abstractmethod
    async def delete(self, account_id: UUID) -> bool:
        """소셜 계정 삭제."""
        pass


class TokenServiceInterface(ABC):
    """JWT 토큰 서비스 인터페이스."""

    @abstractmethod
    def create_access_token(
        self, user_id: UUID, email: str, user_level: int
    ) -> dict:
        pass

    @abstractmethod
    def create_refresh_token(self, user_id: UUID) -> dict:
        pass

    @abstractmethod
    async def verify_token(self, token: str) -> dict:
        pass

    @abstractmethod
    async def blacklist_token(self, token: str) -> None:
        pass


class AuthCacheInterface(ABC):
    """인증 캐시 인터페이스."""

    @abstractmethod
    async def set_jwt_session(
        self, user_id: UUID, session_data: dict, expire: int
    ) -> None:
        pass

    @abstractmethod
    async def get_jwt_session(self, user_id: UUID) -> Optional[dict]:
        pass

    @abstractmethod
    async def delete_jwt_session(self, user_id: UUID) -> None:
        pass

    @abstractmethod
    async def blacklist_jwt_token(self, jti: str, expire: int) -> None:
        pass

    @abstractmethod
    async def is_jwt_token_blacklisted(self, jti: str) -> bool:
        pass

    @abstractmethod
    async def set_oauth_state(
        self, state_token: str, state_data: dict, expire: int
    ) -> None:
        pass

    @abstractmethod
    async def get_oauth_state(self, state_token: str) -> Optional[dict]:
        pass

    @abstractmethod
    async def delete_oauth_state(self, state_token: str) -> None:
        pass

    @abstractmethod
    async def set_google_access_token(
        self, user_id: UUID, access_token: str, expire: int
    ) -> None:
        pass

    @abstractmethod
    async def get_google_access_token(self, user_id: UUID) -> Optional[str]:
        pass

    @abstractmethod
    async def set_google_refresh_token(
        self, user_id: UUID, refresh_token: str
    ) -> None:
        pass

    @abstractmethod
    async def get_google_refresh_token(self, user_id: UUID) -> Optional[str]:
        pass

    @abstractmethod
    async def delete_google_auth_data(self, user_id: UUID) -> None:
        pass


class OAuthProviderInterface(ABC):
    """외부 OAuth 제공자 인터페이스 (예: Google)."""

    @abstractmethod
    async def generate_auth_url(self) -> tuple[str, str]:
        """Authorization URL과 state 생성."""
        pass

    @abstractmethod
    async def verify_state(self, state: str) -> bool:
        """state 검증."""
        pass

    @abstractmethod
    async def exchange_code_for_tokens(self, code: str) -> dict:
        """가입 대기 중인 코드로 토큰 교환."""
        pass

    @abstractmethod
    async def get_user_info(self, access_token: str) -> dict:
        """액세스 토큰으로 사용자 정보 조회."""
        pass

    @abstractmethod
    async def refresh_access_token(self, refresh_token: str) -> dict:
        """리프레시 토큰으로 액세스 토큰 갱신."""
        pass

    @abstractmethod
    async def revoke_token(self, token: str) -> bool:
        """토큰 취소."""
        pass
