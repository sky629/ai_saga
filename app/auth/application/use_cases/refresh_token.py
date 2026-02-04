"""Refresh Token Use Case."""

from uuid import UUID

from pydantic import BaseModel

from app.auth.application.ports import (
    AuthCacheInterface,
    TokenServiceInterface,
)
from app.common.exception import Unauthorized


class RefreshTokenInput(BaseModel):
    refresh_token: str


class RefreshTokenResult(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class RefreshTokenUseCase:
    """JWT 액세스 토큰 갱신 유스케이스."""

    def __init__(
        self, token_service: TokenServiceInterface, cache: AuthCacheInterface
    ):
        self._token_service = token_service
        self._cache = cache

    async def execute(
        self, input_data: RefreshTokenInput
    ) -> RefreshTokenResult:
        payload = await self._token_service.verify_token(
            input_data.refresh_token
        )
        if payload.get("type") != "refresh":
            raise Unauthorized(message="Invalid refresh token")

        user_id = UUID(payload.get("sub"))
        session_data = await self._cache.get_jwt_session(user_id)
        if not session_data:
            raise Unauthorized(message="Session expired")

        new_token = self._token_service.create_access_token(
            user_id=user_id,
            email=session_data["email"],
            user_level=session_data["user_level"],
        )
        return RefreshTokenResult(
            access_token=new_token["access_token"],
            token_type=new_token["token_type"],
            expires_in=new_token["expires_in"],
        )
