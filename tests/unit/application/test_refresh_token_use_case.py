"""RefreshTokenUseCase 단위 테스트."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.auth.application.use_cases.refresh_token import (
    RefreshTokenInput,
    RefreshTokenUseCase,
)
from app.common.exception import Unauthorized


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def token_service():
    mock = MagicMock()
    mock.verify_token = AsyncMock()
    mock.blacklist_token = AsyncMock()
    return mock


@pytest.fixture
def cache():
    mock = AsyncMock()
    return mock


@pytest.fixture
def use_case(token_service, cache):
    return RefreshTokenUseCase(token_service=token_service, cache=cache)


@pytest.mark.asyncio
async def test_refresh_token_rotates_and_renews_session(
    use_case, token_service, cache, user_id
):
    token_service.verify_token.return_value = {
        "sub": str(user_id),
        "type": "refresh",
    }
    cache.get_jwt_session.return_value = {
        "email": "test@example.com",
        "user_level": 1,
    }
    token_service.create_access_token.return_value = {
        "access_token": "new-access-token",
        "token_type": "bearer",
        "expires_in": 1800,
    }
    token_service.create_refresh_token.return_value = {
        "refresh_token": "new-refresh-token",
        "expires_in": 86400,
    }

    result = await use_case.execute(
        RefreshTokenInput(refresh_token="old-refresh-token")
    )

    assert result.access_token == "new-access-token"
    assert result.refresh_token == "new-refresh-token"
    token_service.blacklist_token.assert_awaited_once_with("old-refresh-token")
    cache.set_jwt_session.assert_awaited_once_with(
        user_id=user_id,
        session_data={"email": "test@example.com", "user_level": 1},
        expire=86400,
    )


@pytest.mark.asyncio
async def test_refresh_token_rejects_non_refresh_type(
    use_case, token_service, cache, user_id
):
    token_service.verify_token.return_value = {
        "sub": str(user_id),
        "type": "access",
    }

    with pytest.raises(Unauthorized, match="Invalid refresh token"):
        await use_case.execute(RefreshTokenInput(refresh_token="bad-token"))

    cache.get_jwt_session.assert_not_called()


@pytest.mark.asyncio
async def test_refresh_token_rejects_expired_session(
    use_case, token_service, cache, user_id
):
    token_service.verify_token.return_value = {
        "sub": str(user_id),
        "type": "refresh",
    }
    cache.get_jwt_session.return_value = None

    with pytest.raises(Unauthorized, match="Session expired"):
        await use_case.execute(
            RefreshTokenInput(refresh_token="refresh-token")
        )

    token_service.create_access_token.assert_not_called()
