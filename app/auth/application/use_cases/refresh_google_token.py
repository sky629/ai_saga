"""Refresh Google Token Use Case."""

from typing import Any, Dict
from uuid import UUID

from app.auth.application.ports import (
    AuthCacheInterface,
    OAuthProviderInterface,
)
from app.common.exception import BadRequest


class RefreshGoogleTokenUseCase:
    """Google 액세스 토큰 갱신 유스케이스."""

    def __init__(
        self, oauth_provider: OAuthProviderInterface, cache: AuthCacheInterface
    ):
        self._oauth_provider = oauth_provider
        self._cache = cache

    async def execute(self, user_id: UUID) -> Dict[str, Any]:
        refresh_token = await self._cache.get_google_refresh_token(user_id)
        if not refresh_token:
            raise BadRequest(message="No Google refresh token found")

        new_tokens = await self._oauth_provider.refresh_access_token(
            refresh_token
        )

        # Update cache
        expires_in = new_tokens.get("expires_in", 3600)
        await self._cache.set_google_access_token(
            user_id, new_tokens["access_token"], expire=expires_in
        )

        if "refresh_token" in new_tokens:
            await self._cache.set_google_refresh_token(
                user_id, new_tokens["refresh_token"]
            )

        return new_tokens
