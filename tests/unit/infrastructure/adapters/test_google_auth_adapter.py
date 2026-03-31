"""GoogleAuthAdapter 단위 테스트."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
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


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload
        self.text = str(payload)
        self.status_code = 200

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class _FakeAsyncClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.request = AsyncMock(side_effect=self._responses)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_get_user_info_retries_after_timeout_and_succeeds():
    cache = MagicMock(spec=AuthCacheInterface)
    adapter = GoogleAuthAdapter(cache=cache)
    request = httpx.Request("GET", adapter.userinfo_endpoint)

    fake_client = _FakeAsyncClient(
        [
            httpx.ReadTimeout("timed out", request=request),
            _FakeResponse(
                {
                    "email": "test@example.com",
                    "id": "provider-user-1",
                }
            ),
        ]
    )

    with patch(
        "app.auth.infrastructure.adapters.google_auth_adapter.httpx.AsyncClient",
        return_value=fake_client,
    ):
        user_info = await adapter.get_user_info("access-token")

    assert user_info["email"] == "test@example.com"
    assert fake_client.request.await_count == 2


@pytest.mark.asyncio
async def test_get_user_info_raises_server_error_after_retry_exhaustion():
    cache = MagicMock(spec=AuthCacheInterface)
    adapter = GoogleAuthAdapter(cache=cache)
    request = httpx.Request("GET", adapter.userinfo_endpoint)

    fake_client = _FakeAsyncClient(
        [
            httpx.ReadTimeout("timed out", request=request),
            httpx.ReadTimeout("timed out", request=request),
            httpx.ReadTimeout("timed out", request=request),
        ]
    )

    with patch(
        "app.auth.infrastructure.adapters.google_auth_adapter.httpx.AsyncClient",
        return_value=fake_client,
    ):
        with pytest.raises(
            Exception, match="Failed to fetch user information"
        ):
            await adapter.get_user_info("access-token")

    assert fake_client.request.await_count == 3
