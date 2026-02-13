"""Simple integration test for Redis cache functionality."""

import pytest

from app.game.infrastructure.adapters import CacheServiceAdapter


class TestRedisCacheBasic:
    """기본 Redis 캐시 동작 확인."""

    @pytest.mark.asyncio
    async def test_redis_connection(self):
        """Redis 연결 확인."""
        cache = CacheServiceAdapter()

        # Set and get
        await cache.set("test:key", "test_value", ttl_seconds=10)
        result = await cache.get("test:key")

        assert result == "test_value"

        # Cleanup
        await cache.delete("test:key")

    @pytest.mark.asyncio
    async def test_cache_miss_returns_none(self):
        """존재하지 않는 키는 None 반환."""
        cache = CacheServiceAdapter()
        result = await cache.get("test:nonexistent:key")
        assert result is None
