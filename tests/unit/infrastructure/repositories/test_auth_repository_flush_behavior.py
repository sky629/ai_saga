from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.domain.entities import SocialAccountEntity, UserEntity
from app.auth.domain.value_objects import AuthProvider, UserLevel
from app.auth.infrastructure.repositories.social_account_repository import (
    SocialAccountRepositoryImpl,
)
from app.auth.infrastructure.repositories.user_repository import (
    UserRepositoryImpl,
)


def _build_user(now: datetime) -> UserEntity:
    return UserEntity(
        id=uuid4(),
        email="user@example.com",
        name="User",
        profile_image_url=None,
        user_level=UserLevel.NORMAL,
        is_active=True,
        email_verified=True,
        created_at=now,
        updated_at=now,
        last_login_at=now,
    )


def _build_user_orm(user: UserEntity) -> SimpleNamespace:
    return SimpleNamespace(
        id=user.id,
        email=user.email,
        name=user.name,
        profile_image_url=user.profile_image_url,
        user_level=user.user_level.value,
        is_active=user.is_active,
        email_verified=user.email_verified,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at,
        game_level=user.game_level,
        game_experience=user.game_experience,
        game_current_experience=user.game_current_experience,
    )


def _build_social_account(now: datetime) -> SocialAccountEntity:
    return SocialAccountEntity(
        id=uuid4(),
        user_id=uuid4(),
        provider=AuthProvider.GOOGLE,
        provider_user_id="provider-user-id",
        provider_data={"sub": "provider-user-id"},
        created_at=now,
        updated_at=now,
        last_used_at=now,
        scope_granted=["email"],
        is_primary=True,
    )


def _build_social_account_orm(
    account: SocialAccountEntity,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=account.id,
        user_id=account.user_id,
        provider=account.provider.value,
        provider_user_id=account.provider_user_id,
        provider_data=account.provider_data,
        scope_granted=account.scope_granted,
        is_primary=account.is_primary,
        connected_at=account.created_at,
        last_used_at=account.last_used_at,
    )


@pytest.mark.asyncio
async def test_user_repository_save_uses_flush_not_commit():
    now = datetime.now(UTC)
    user = _build_user(now)
    orm = _build_user_orm(user)

    db = MagicMock(spec=AsyncSession)
    db.execute = AsyncMock(
        return_value=SimpleNamespace(scalar_one_or_none=lambda: orm)
    )
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    repo = UserRepositoryImpl(db)

    saved = await repo.save(user)

    db.flush.assert_awaited_once()
    db.commit.assert_not_called()
    db.refresh.assert_awaited_once_with(orm)
    assert saved.id == user.id


@pytest.mark.asyncio
async def test_user_repository_update_last_login_uses_flush_not_commit():
    db = MagicMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    repo = UserRepositoryImpl(db)

    await repo.update_last_login(uuid4(), datetime.now(UTC))

    db.flush.assert_awaited_once()
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_social_account_repository_save_uses_flush_not_commit():
    now = datetime.now(UTC)
    account = _build_social_account(now)
    orm = _build_social_account_orm(account)

    db = MagicMock(spec=AsyncSession)
    db.execute = AsyncMock(
        return_value=SimpleNamespace(scalar_one_or_none=lambda: orm)
    )
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    repo = SocialAccountRepositoryImpl(db)

    saved = await repo.save(account)

    db.flush.assert_awaited_once()
    db.commit.assert_not_called()
    db.refresh.assert_awaited_once_with(orm)
    assert saved.id == account.id


@pytest.mark.asyncio
async def test_social_account_repository_delete_uses_flush_not_commit():
    db = MagicMock(spec=AsyncSession)
    db.execute = AsyncMock(return_value=SimpleNamespace(rowcount=1))
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    repo = SocialAccountRepositoryImpl(db)

    deleted = await repo.delete(uuid4())

    db.flush.assert_awaited_once()
    db.commit.assert_not_called()
    assert deleted is True
