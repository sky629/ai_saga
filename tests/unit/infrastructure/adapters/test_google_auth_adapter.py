"""GoogleAuthAdapter 단위 테스트."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.auth.application.ports import AuthCacheInterface
from app.auth.infrastructure.adapters.google_auth_adapter import (
    GoogleAuthAdapter,
)


@pytest.mark.asyncio
async def test_verify_state_uses_consume_and_returns_true_for_google():
    cache = MagicMock(spec=AuthCacheInterface)
    cache.consume_oauth_state = AsyncMock(return_value={"provider": "google"})

    adapter = GoogleAuthAdapter(cache=cache)

    result = await adapter.verify_state("state-token")

    assert result is True
    cache.consume_oauth_state.assert_awaited_once_with("state-token")
    cache.get_oauth_state.assert_not_called()
    cache.delete_oauth_state.assert_not_called()


@pytest.mark.asyncio
async def test_verify_state_returns_false_when_state_missing():
    cache = MagicMock(spec=AuthCacheInterface)
    cache.consume_oauth_state = AsyncMock(return_value=None)

    adapter = GoogleAuthAdapter(cache=cache)

    result = await adapter.verify_state("state-token")

    assert result is False
    cache.consume_oauth_state.assert_awaited_once_with("state-token")


@pytest.mark.asyncio
async def test_verify_state_rejects_provider_mismatch():
    cache = MagicMock(spec=AuthCacheInterface)
    cache.consume_oauth_state = AsyncMock(return_value={"provider": "github"})

    adapter = GoogleAuthAdapter(cache=cache)

    result = await adapter.verify_state("state-token")

    assert result is False
    cache.consume_oauth_state.assert_awaited_once_with("state-token")
