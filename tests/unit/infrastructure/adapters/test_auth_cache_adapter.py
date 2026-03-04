"""AuthCacheAdapter 단위 테스트."""

from unittest.mock import AsyncMock

import pytest
import rapidjson

from app.auth.infrastructure.adapters.auth_cache_adapter import (
    AuthCacheAdapter,
)


class _FakeRedisConnection:
    def __init__(self, initial_store: dict[str, str | bytes] | None = None):
        self._store = initial_store or {}

    async def set(self, key: str, value: str, ex: int):
        self._store[key] = value

    async def eval(self, script: str, numkeys: int, key: str):
        assert numkeys == 1
        assert "GET" in script
        assert "DEL" in script

        value = self._store.get(key)
        if value is not None:
            del self._store[key]
        return value


@pytest.mark.asyncio
async def test_consume_oauth_state_returns_value_once_then_none():
    adapter = AuthCacheAdapter()
    state_key = adapter._get_key("oauth_state:state-token")

    redis_conn = _FakeRedisConnection(
        {
            state_key: rapidjson.dumps(
                {
                    "provider": "google",
                    "created_at": 1730000000,
                }
            )
        }
    )
    adapter.get_connection = AsyncMock(return_value=redis_conn)

    first = await adapter.consume_oauth_state("state-token")
    second = await adapter.consume_oauth_state("state-token")

    assert first == {"provider": "google", "created_at": 1730000000}
    assert second is None


@pytest.mark.asyncio
async def test_consume_oauth_state_parses_bytes_payload():
    adapter = AuthCacheAdapter()
    state_key = adapter._get_key("oauth_state:state-token")

    redis_conn = _FakeRedisConnection(
        {
            state_key: rapidjson.dumps(
                {
                    "provider": "google",
                    "created_at": 1730000000,
                }
            ).encode("utf-8")
        }
    )
    adapter.get_connection = AsyncMock(return_value=redis_conn)

    state_data = await adapter.consume_oauth_state("state-token")

    assert state_data == {"provider": "google", "created_at": 1730000000}


@pytest.mark.asyncio
async def test_set_oauth_state_can_be_consumed_once():
    adapter = AuthCacheAdapter()
    redis_conn = _FakeRedisConnection()
    adapter.get_connection = AsyncMock(return_value=redis_conn)

    await adapter.set_oauth_state(
        "state-token",
        {"provider": "google", "created_at": 1730000000},
        expire=600,
    )

    first = await adapter.consume_oauth_state("state-token")
    second = await adapter.consume_oauth_state("state-token")

    assert first == {"provider": "google", "created_at": 1730000000}
    assert second is None
