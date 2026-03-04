"""HandleOAuthCallbackUseCase 단위 테스트."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.auth.application.use_cases.handle_oauth_callback import (
    HandleOAuthCallbackUseCase,
    OAuthCallbackInput,
)
from app.auth.domain.entities.user import UserEntity
from app.auth.domain.value_objects import AuthProvider, UserLevel
from app.common.utils.datetime import get_utc_datetime
from app.common.utils.id_generator import get_uuid7
from config.settings import settings


@pytest.mark.asyncio
async def test_oauth_callback_sets_session_ttl_with_session_policy():
    user_id = get_uuid7()
    now = get_utc_datetime()

    user_repo = AsyncMock()
    social_repo = AsyncMock()
    oauth_provider = AsyncMock()
    token_service = MagicMock()
    cache = AsyncMock()

    oauth_provider.verify_state.return_value = True
    oauth_provider.exchange_code_for_tokens.return_value = {
        "access_token": "google-access",
        "refresh_token": "google-refresh",
        "expires_in": 3600,
    }
    oauth_provider.get_user_info.return_value = {
        "email": "test@example.com",
        "id": "provider-user-1",
        "name": "tester",
        "verified_email": True,
    }

    social_repo.get_by_provider.return_value = SimpleNamespace(user_id=user_id)
    user_repo.get_by_id.return_value = UserEntity(
        id=user_id,
        email="test@example.com",
        name="tester",
        profile_image_url=None,
        user_level=UserLevel.NORMAL,
        is_active=True,
        email_verified=True,
        created_at=now,
        updated_at=now,
        last_login_at=now,
    )
    token_service.create_access_token.return_value = {
        "access_token": "jwt-access",
        "token_type": "bearer",
        "expires_in": 1800,
    }
    token_service.create_refresh_token.return_value = {
        "refresh_token": "jwt-refresh",
        "expires_in": 86400,
    }

    use_case = HandleOAuthCallbackUseCase(
        user_repo=user_repo,
        social_repo=social_repo,
        oauth_provider=oauth_provider,
        token_service=token_service,
        cache=cache,
    )

    await use_case.execute(
        OAuthCallbackInput(
            code="oauth-code",
            state="oauth-state",
            provider=AuthProvider.GOOGLE,
        )
    )

    cache.set_jwt_session.assert_awaited_once_with(
        user_id=user_id,
        session_data={
            "email": "test@example.com",
            "user_level": UserLevel.NORMAL.value,
        },
        expire=settings.jwt_session_expire_minutes * 60,
    )


@pytest.mark.asyncio
async def test_oauth_callback_recovers_on_social_save_race_for_same_user():
    user_id = get_uuid7()
    now = get_utc_datetime()

    user_repo = AsyncMock()
    social_repo = AsyncMock()
    oauth_provider = AsyncMock()
    token_service = MagicMock()
    cache = AsyncMock()

    oauth_provider.verify_state.return_value = True
    oauth_provider.exchange_code_for_tokens.return_value = {
        "access_token": "google-access",
        "refresh_token": "google-refresh",
        "expires_in": 3600,
    }
    oauth_provider.get_user_info.return_value = {
        "email": "test@example.com",
        "id": "provider-user-1",
        "name": "tester",
        "verified_email": True,
    }

    existing_user = UserEntity(
        id=user_id,
        email="test@example.com",
        name="tester",
        profile_image_url="https://cdn/image.png",
        user_level=UserLevel.NORMAL,
        is_active=True,
        email_verified=True,
        created_at=now,
        updated_at=now,
        last_login_at=now,
    )
    user_repo.get_by_email.return_value = existing_user

    # 1차 조회에서는 없음, 저장 충돌 후 재조회에서는 같은 유저 계정 발견
    social_repo.get_by_provider.side_effect = [
        None,
        SimpleNamespace(user_id=user_id),
    ]
    social_repo.save.side_effect = RuntimeError("duplicate social account")

    token_service.create_access_token.return_value = {
        "access_token": "jwt-access",
        "token_type": "bearer",
        "expires_in": 1800,
    }
    token_service.create_refresh_token.return_value = {
        "refresh_token": "jwt-refresh",
        "expires_in": 86400,
    }

    use_case = HandleOAuthCallbackUseCase(
        user_repo=user_repo,
        social_repo=social_repo,
        oauth_provider=oauth_provider,
        token_service=token_service,
        cache=cache,
    )

    result = await use_case.execute(
        OAuthCallbackInput(
            code="oauth-code",
            state="oauth-state",
            provider=AuthProvider.GOOGLE,
        )
    )

    assert result.user.id == user_id
    social_repo.save.assert_awaited_once()
    cache.set_jwt_session.assert_awaited_once()


@pytest.mark.asyncio
async def test_oauth_callback_raises_when_social_save_race_binds_other_user():
    user_id = get_uuid7()
    other_user_id = get_uuid7()
    now = get_utc_datetime()

    user_repo = AsyncMock()
    social_repo = AsyncMock()
    oauth_provider = AsyncMock()
    token_service = MagicMock()
    cache = AsyncMock()

    oauth_provider.verify_state.return_value = True
    oauth_provider.exchange_code_for_tokens.return_value = {
        "access_token": "google-access",
        "refresh_token": "google-refresh",
        "expires_in": 3600,
    }
    oauth_provider.get_user_info.return_value = {
        "email": "test@example.com",
        "id": "provider-user-1",
        "name": "tester",
        "verified_email": True,
    }

    existing_user = UserEntity(
        id=user_id,
        email="test@example.com",
        name="tester",
        profile_image_url="https://cdn/image.png",
        user_level=UserLevel.NORMAL,
        is_active=True,
        email_verified=True,
        created_at=now,
        updated_at=now,
        last_login_at=now,
    )
    user_repo.get_by_email.return_value = existing_user

    social_repo.get_by_provider.side_effect = [
        None,
        SimpleNamespace(user_id=other_user_id),
    ]
    social_repo.save.side_effect = RuntimeError("duplicate social account")

    token_service.create_access_token.return_value = {
        "access_token": "jwt-access",
        "token_type": "bearer",
        "expires_in": 1800,
    }
    token_service.create_refresh_token.return_value = {
        "refresh_token": "jwt-refresh",
        "expires_in": 86400,
    }

    use_case = HandleOAuthCallbackUseCase(
        user_repo=user_repo,
        social_repo=social_repo,
        oauth_provider=oauth_provider,
        token_service=token_service,
        cache=cache,
    )

    with pytest.raises(RuntimeError, match="duplicate social account"):
        await use_case.execute(
            OAuthCallbackInput(
                code="oauth-code",
                state="oauth-state",
                provider=AuthProvider.GOOGLE,
            )
        )
