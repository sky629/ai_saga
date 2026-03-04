from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.common.exception import Conflict
from app.game.infrastructure.adapters.cache_service import CacheServiceAdapter


@pytest.mark.asyncio
async def test_lock_does_not_enter_context_when_acquire_fails(monkeypatch):
    lock_obj = AsyncMock()
    lock_obj.acquire.return_value = False

    redis = SimpleNamespace(lock=lambda *args, **kwargs: lock_obj)

    async def mock_get_connection():
        return redis

    monkeypatch.setattr(
        "app.game.infrastructure.adapters.cache_service.pools.get_connection",
        mock_get_connection,
    )

    service = CacheServiceAdapter()

    with pytest.raises(Conflict):
        async with service.lock("busy-key", ttl_ms=1000):
            raise AssertionError("should not enter critical section")
