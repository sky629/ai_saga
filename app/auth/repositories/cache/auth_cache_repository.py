"""Authentication cache repository using Redis."""

import asyncio
import uuid
from typing import Any, Dict, Optional, Union

from app.common.storage.redis import CacheExpire, _CacheClient


class AuthCacheRepository(_CacheClient):
    """Cache repository for authentication data."""

    _alias: str = "auth"
    _ttl: Union[int, CacheExpire] = CacheExpire.HOUR  # Default 1 hour

    def _get_key(self, key: str) -> str:
        """Generate cache key."""
        return f"{self._alias}:{key}"

    # JWT Token Management
    async def set_jwt_session(
        self,
        user_id: uuid.UUID,
        session_data: Dict[str, Any],
        expire: Optional[int] = None,
    ) -> None:
        """Set JWT session data."""
        key = self._get_key(f"session:{user_id.hex}")
        await self.set(key, value=session_data, expire=expire or self._ttl)

    async def get_jwt_session(self, user_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """Get JWT session data."""
        key = self._get_key(f"session:{user_id.hex}")
        return await self.get(key)

    async def delete_jwt_session(self, user_id: uuid.UUID) -> None:
        """Delete JWT session data."""
        key = self._get_key(f"session:{user_id.hex}")
        await self.delete(key)

    # JWT Token Blacklist
    async def blacklist_jwt_token(self, jti: str, expire: int) -> None:
        """Add JWT token to blacklist."""
        key = self._get_key(f"blacklist:{jti}")
        await self.set(key, value=True, expire=expire)

    async def is_jwt_token_blacklisted(self, jti: str) -> bool:
        """Check if JWT token is blacklisted."""
        key = self._get_key(f"blacklist:{jti}")
        result = await self.get(key)
        return result is not None

    # OAuth State Management
    async def set_oauth_state(
        self,
        state_token: str,
        state_data: Dict[str, Any],
        expire: int = CacheExpire.MINUTE * 10,  # 10 minutes
    ) -> None:
        """Set OAuth state data."""
        key = self._get_key(f"oauth_state:{state_token}")
        await self.set(key, value=state_data, expire=expire)

    async def get_oauth_state(self, state_token: str) -> Optional[Dict[str, Any]]:
        """Get OAuth state data."""
        key = self._get_key(f"oauth_state:{state_token}")
        return await self.get(key)

    async def delete_oauth_state(self, state_token: str) -> None:
        """Delete OAuth state data."""
        key = self._get_key(f"oauth_state:{state_token}")
        await self.delete(key)

    # Google OAuth Token Management
    async def set_google_access_token(
        self,
        user_id: uuid.UUID,
        access_token: str,
        expire: int = 3600,  # 1 hour
    ) -> None:
        """Set Google access token."""
        key = self._get_key(f"google_access_token:{user_id.hex}")
        await self.set(key, value=access_token, expire=expire)

    async def get_google_access_token(self, user_id: uuid.UUID) -> Optional[str]:
        """Get Google access token."""
        key = self._get_key(f"google_access_token:{user_id.hex}")
        return await self.get(key)

    async def delete_google_access_token(self, user_id: uuid.UUID) -> None:
        """Delete Google access token."""
        key = self._get_key(f"google_access_token:{user_id.hex}")
        await self.delete(key)

    async def set_google_refresh_token(
        self,
        user_id: uuid.UUID,
        refresh_token: str,
        expire: int = CacheExpire.MONTH,  # 30 days
    ) -> None:
        """Set Google refresh token."""
        key = self._get_key(f"google_refresh_token:{user_id.hex}")
        await self.set(key, value=refresh_token, expire=expire)

    async def get_google_refresh_token(self, user_id: uuid.UUID) -> Optional[str]:
        """Get Google refresh token."""
        key = self._get_key(f"google_refresh_token:{user_id.hex}")
        return await self.get(key)

    async def delete_google_refresh_token(self, user_id: uuid.UUID) -> None:
        """Delete Google refresh token."""
        key = self._get_key(f"google_refresh_token:{user_id.hex}")
        await self.delete(key)

    # User Session Management
    async def set_user_session(
        self,
        user_id: uuid.UUID,
        session_data: Dict[str, Any],
        expire: int = CacheExpire.DAY,  # 1 day
    ) -> None:
        """Set user session data."""
        key = self._get_key(f"user_session:{user_id.hex}")
        await self.set(key, value=session_data, expire=expire)

    async def get_user_session(self, user_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """Get user session data."""
        key = self._get_key(f"user_session:{user_id.hex}")
        return await self.get(key)

    async def delete_user_session(self, user_id: uuid.UUID) -> None:
        """Delete user session data."""
        key = self._get_key(f"user_session:{user_id.hex}")
        await self.delete(key)

    # Utility methods
    async def clear_user_auth_data(self, user_id: uuid.UUID) -> None:
        """Clear all authentication data for a user."""
        await asyncio.gather(
            self.delete_jwt_session(user_id),
            self.delete_google_access_token(user_id),
            self.delete_google_refresh_token(user_id),
            self.delete_user_session(user_id),
        )


# Global instance
auth_cache = AuthCacheRepository()
