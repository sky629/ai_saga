"""Social account repository for database operations."""

import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from app.auth.models.postgres_models import SocialAccount
from app.common.storage.base_postgres import BaseRepository
from app.common.storage.postgres import handle_postgres_error, postgres_storage
from app.common.utils.datetime import get_utc_datetime


class SocialAccountRepository(BaseRepository):
    """Repository for social account database operations."""

    model_class = SocialAccount
    domain = "user"

    @classmethod
    @handle_postgres_error
    async def create_social_account(
        cls,
        user_id: uuid.UUID,
        provider: str,
        provider_user_id: str,
        provider_data: Optional[Dict[str, Any]] = None,
        scope_granted: Optional[List[str]] = None,
        is_primary: bool = True,
    ) -> SocialAccount:
        """Create a new social account."""

        social_account = SocialAccount(
            id=uuid.uuid4(),
            user_id=user_id,
            provider=provider,
            provider_user_id=provider_user_id,
            provider_data=provider_data,
            scope_granted=scope_granted,
            is_primary=is_primary,
        )
        return await cls.create(social_account)

    @classmethod
    @handle_postgres_error
    async def get_social_account_by_id(
        cls, account_id: uuid.UUID
    ) -> Optional[SocialAccount]:
        """Get social account by ID."""
        return await cls.get_by_id(account_id.hex)

    @classmethod
    @handle_postgres_error
    async def get_social_account_by_provider(
        cls, provider: str, provider_user_id: str
    ) -> Optional[SocialAccount]:
        """Get social account by provider and provider user ID."""
        async with postgres_storage.get_domain_read_session(
            domain=cls.domain
        ) as session:
            result = await session.execute(
                select(cls.model_class).where(
                    cls.model_class.provider == provider,
                    cls.model_class.provider_user_id == provider_user_id,
                )
            )
            return result.scalar_one_or_none()

    @classmethod
    @handle_postgres_error
    async def get_user_social_accounts(
        cls, user_id: uuid.UUID, provider: Optional[str] = None
    ) -> List[SocialAccount]:
        """Get all social accounts for a user, optionally filtered by provider."""
        async with postgres_storage.get_domain_read_session(
            domain=cls.domain
        ) as session:
            stmt = select(cls.model_class).where(cls.model_class.user_id == user_id)

            if provider:
                stmt = stmt.where(cls.model_class.provider == provider)

            result = await session.execute(stmt)
            return list(result.scalars().all())

    @classmethod
    @handle_postgres_error
    async def update_social_account(
        cls, account_id: uuid.UUID, **kwargs
    ) -> Optional[SocialAccount]:
        """Update social account information."""
        return await cls.update_by_id(account_id.hex, **kwargs)

    @classmethod
    @handle_postgres_error
    async def update_last_used(cls, account_id: uuid.UUID) -> None:
        """Update social account's last used timestamp."""
        data = {"last_used_at": get_utc_datetime()}
        return await cls.update_by_id(account_id.hex, **data)

    @classmethod
    @handle_postgres_error
    async def delete_social_account(cls, account_id: uuid.UUID) -> bool:
        """Delete social account."""
        return await cls.delete_by_id(account_id.hex)

    @classmethod
    @handle_postgres_error
    async def delete_user_social_accounts(cls, user_id: uuid.UUID) -> int:
        """Delete all social accounts for a user."""
        return await cls.delete_by_field("user_id", user_id.hex)
