"""Regression tests for Google OAuth state verification flow."""

from unittest.mock import AsyncMock
from urllib.parse import parse_qs, urlparse

import pytest

from app.auth.infrastructure.adapters.auth_cache_adapter import (
    AuthCacheAdapter,
)
from app.auth.infrastructure.adapters.google_auth_adapter import (
    GoogleAuthAdapter,
)


class _FakeRedisConnection:
    def __init__(self):
        self._store: dict[str, bytes] = {}

    async def set(self, key: str, value: str, ex: int):
        del ex
        # Emulate decode_responses=False: Lua EVAL returns bytes.
        self._store[key] = value.encode("utf-8")

    async def eval(self, script: str, numkeys: int, key: str):
        assert numkeys == 1
        assert "GET" in script
        assert "DEL" in script

        value = self._store.get(key)
        if value is not None:
            del self._store[key]
        return value


@pytest.mark.asyncio
async def test_google_oauth_state_round_trip_accepts_bytes_payload():
    cache = AuthCacheAdapter()
    redis_conn = _FakeRedisConnection()
    cache.get_connection = AsyncMock(return_value=redis_conn)

    adapter = GoogleAuthAdapter(cache=cache)
    adapter.client_id = "test-client-id"
    adapter.redirect_uri = "http://localhost:8000/api/v1/auth/google/callback/"

    auth_url, generated_state = await adapter.generate_auth_url()

    query = parse_qs(urlparse(auth_url).query)
    assert query["state"] == [generated_state]

    assert await adapter.verify_state(generated_state) is True
    assert await adapter.verify_state(generated_state) is False
