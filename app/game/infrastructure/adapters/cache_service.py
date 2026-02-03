"""Cache Service Adapter.

Redis를 Port 인터페이스에 맞춰 래핑합니다.
"""

from typing import Optional

from app.common.storage.redis import pools
from app.game.application.ports import CacheServiceInterface


class CacheServiceAdapter(CacheServiceInterface):
    """캐시 서비스 어댑터.
    
    Redis를 Port 인터페이스에 맞춰 래핑합니다.
    멱등성 키 저장 등에 사용됩니다.
    """

    async def get(self, key: str) -> Optional[str]:
        """캐시 조회."""
        redis = await pools.get_connection()
        return await redis.get(key)

    async def set(self, key: str, value: str, ttl_seconds: int = 600) -> None:
        """캐시 저장."""
        redis = await pools.get_connection()
        await redis.set(key, value, ex=ttl_seconds)
