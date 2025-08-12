"""User repository for database operations."""

import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.auth.models.postgres_models import User
from app.common.storage.base_postgres import BaseRepository
from app.common.storage.postgres import handle_postgres_error, postgres_storage
from app.common.utils.datetime import get_utc_datetime


class UserRepository(BaseRepository):
    """Repository for user database operations."""

    model_class = User
    domain = "user"

    @classmethod
    async def create_user(
        cls,
        email: str,
        name: str,
        profile_image_url: Optional[str] = None,
        user_level: int = 100,
        email_verified: bool = False,
    ) -> User:
        """Create a new user."""
        user = User(
            id=uuid.uuid4(),
            email=email,
            name=name,
            profile_image_url=profile_image_url,
            user_level=user_level,
            email_verified=email_verified,
        )
        await cls.create(user)
        return user

    @classmethod
    @handle_postgres_error
    async def get_user_by_id(cls, user_id: uuid.UUID) -> Optional[User]:
        """Get user by ID."""
        return await cls.get_by_id(user_id.hex)

    @classmethod
    @handle_postgres_error
    async def get_user_by_email(cls, email: str) -> Optional[User]:
        """Get user by email."""
        return await cls.get_by_field(field_name="email", field_value=email.lower())

    @classmethod
    @handle_postgres_error
    async def get_user_with_social_accounts(cls, user_id: uuid.UUID) -> Optional[User]:
        """Get user with all social accounts."""
        async with postgres_storage.get_domain_read_session(
            domain=cls.domain
        ) as session:
            result = await session.execute(
                select(User)
                .options(selectinload(User.social_accounts))
                .where(User.id == user_id)
            )
            return result.scalar_one_or_none()

    @classmethod
    @handle_postgres_error
    async def update_user(cls, user_id: uuid.UUID, **kwargs) -> Optional[User]:
        """Update user information."""
        kwargs.update({"updated_at": get_utc_datetime()})
        return await cls.update_by_id(user_id, **kwargs)

    @classmethod
    @handle_postgres_error
    async def update_last_login(cls, user_id: uuid.UUID) -> None:
        """Update user's last login timestamp."""
        data = {"updated_at": get_utc_datetime()}
        return await cls.update_by_id(user_id, **data)

    @classmethod
    @handle_postgres_error
    async def delete_user(cls, user_id: uuid.UUID) -> bool:
        """Delete user and all associated data."""
        return await cls.delete_by_id(user_id)

    @classmethod
    @handle_postgres_error
    async def list_users(
        cls,
        limit: int = 100,
        offset: int = 0,
        is_active: Optional[bool] = None,
    ) -> List[User]:
        """List users with pagination."""
        filters = {"is_active": is_active}
        return await cls.list_all(limit=limit, offset=offset, filters=filters)
