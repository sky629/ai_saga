"""Auth Cache Adapter Implementation."""

from typing import Any, Dict, Optional, Union
from uuid import UUID

import rapidjson

from app.auth.application.ports import AuthCacheInterface
from app.common.storage.redis import CacheExpire, _CacheClient


class AuthCacheAdapter(_CacheClient, AuthCacheInterface):
    """Redis 기반 인증 캐시 어댑터."""

    _alias: str = "auth"
    _ttl: Union[int, CacheExpire] = CacheExpire.HOUR

    def _get_key(self, key: str) -> str:
        return f"{self._alias}:{key}"

    async def set_jwt_session(
        self,
        user_id: UUID,
        session_data: Dict[str, Any],
        expire: Optional[int] = None,
    ) -> None:
        key = self._get_key(f"session:{user_id.hex}")
        await self.set(key, value=session_data, expire=expire or self._ttl)

    async def get_jwt_session(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        key = self._get_key(f"session:{user_id.hex}")
        return await self.get(key)

    async def delete_jwt_session(self, user_id: UUID) -> None:
        key = self._get_key(f"session:{user_id.hex}")
        await self.delete(key)

    async def blacklist_jwt_token(self, jti: str, expire: int) -> None:
        key = self._get_key(f"blacklist:{jti}")
        await self.set(key, value=True, expire=expire)

    async def is_jwt_token_blacklisted(self, jti: str) -> bool:
        key = self._get_key(f"blacklist:{jti}")
        result = await self.get(key)
        return result is not None

    async def set_oauth_state(
        self, state_token: str, state_data: Dict[str, Any], expire: int
    ) -> None:
        key = f"oauth_state:{state_token}"
        await self.set(key, value=state_data, expire=expire)

    async def get_oauth_state(
        self, state_token: str
    ) -> Optional[Dict[str, Any]]:
        key = f"oauth_state:{state_token}"
        return await self.get(key)

    async def consume_oauth_state(
        self, state_token: str
    ) -> Optional[Dict[str, Any]]:
        key = self._get_key(f"oauth_state:{state_token}")
        conn = await self.get_connection()
        raw_result = await conn.eval(
            """
            local value = redis.call('GET', KEYS[1])
            if value then
                redis.call('DEL', KEYS[1])
            end
            return value
            """,
            1,
            key,
        )
        if raw_result is None:
            return None

        # Lua EVAL responses can be bytes depending on Redis decoder setup.
        if isinstance(raw_result, (bytes, bytearray, memoryview)):
            raw_result = bytes(raw_result).decode("utf-8")

        return (
            rapidjson.loads(raw_result)
            if isinstance(raw_result, str)
            else None
        )

    async def delete_oauth_state(self, state_token: str) -> None:
        key = f"oauth_state:{state_token}"
        await self.delete(key)

    async def set_google_access_token(
        self, user_id: UUID, access_token: str, expire: int
    ) -> None:
        key = self._get_key(f"google_access_token:{user_id.hex}")
        await self.set(key, value=access_token, expire=expire)

    async def get_google_access_token(self, user_id: UUID) -> Optional[str]:
        key = self._get_key(f"google_access_token:{user_id.hex}")
        return await self.get(key)

    async def set_google_refresh_token(
        self, user_id: UUID, refresh_token: str
    ) -> None:
        key = self._get_key(f"google_refresh_token:{user_id.hex}")
        await self.set(
            key, value=refresh_token, expire=60 * 60 * 24 * 30
        )  # 30 days

    async def get_google_refresh_token(self, user_id: UUID) -> Optional[str]:
        key = self._get_key(f"google_refresh_token:{user_id.hex}")
        return await self.get(key)

    async def delete_google_auth_data(self, user_id: UUID) -> None:
        await self.delete(self._get_key(f"google_access_token:{user_id.hex}"))
        await self.delete(self._get_key(f"google_refresh_token:{user_id.hex}"))
