"""Logout Use Case."""

from uuid import UUID

from pydantic import BaseModel

from app.auth.application.ports import (
    AuthCacheInterface,
    TokenServiceInterface,
)


class LogoutInput(BaseModel):
    user_id: UUID
    access_token: str


class LogoutUseCase:
    """로그아웃 유스케이스."""

    def __init__(
        self,
        token_service: TokenServiceInterface,
        cache: AuthCacheInterface,
    ):
        self._token_service = token_service
        self._cache = cache

    async def execute(self, input_data: LogoutInput) -> None:
        # JWT 블랙리스트 등록
        await self._token_service.blacklist_token(input_data.access_token)
        # 세션 삭제
        await self._cache.delete_jwt_session(input_data.user_id)
        # 소셜 토큰 등 추가 정리 로직이 필요하면 여기서 수행 (현재는 스킵)
