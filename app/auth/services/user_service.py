"""User service for user management operations."""

import uuid
from typing import Any, Dict, Optional, Tuple

from app.auth.models.postgres_models import SocialAccount, User
from app.auth.repositories.cache.auth_cache_repository import auth_cache
from app.auth.repositories.social_account_repository import (
    SocialAccountRepository,
)
from app.auth.repositories.user_repository import UserRepository
from app.common.enums.user_level import UserLevel
from app.common.exception import BadRequest, NotFound
from app.common.logging import logger


class UserService:
    """Service for user management operations."""

    def __init__(self):
        self.user_repo = UserRepository()
        self.social_account_repo = SocialAccountRepository()

    async def create_user_from_google(
        self, google_user_info: Dict[str, Any], provider_data: Dict[str, Any]
    ) -> Tuple[User, SocialAccount, bool]:
        """Create user from Google OAuth data."""
        email = google_user_info["email"]
        name = google_user_info.get("name", email.split("@")[0])
        profile_image_url = google_user_info.get("picture")
        provider_user_id = google_user_info["id"]
        email_verified = google_user_info.get("verified_email", False)

        # Check if user already exists
        existing_user = await self.user_repo.get_user_by_email(email)
        is_new_user = existing_user is None

        if existing_user:
            # Check if Google account is already linked
            existing_social_account = (
                await self.social_account_repo.get_social_account_by_provider(
                    "google", provider_user_id
                )
            )

            if existing_social_account:
                # Update last used timestamp
                await self.social_account_repo.update_last_used(
                    existing_social_account.id
                )
                return existing_user, existing_social_account, False

            # Link Google account to existing user
            social_account = await self.social_account_repo.create_social_account(
                user_id=existing_user.id,
                provider="google",
                provider_user_id=provider_user_id,
                provider_data=provider_data,
                scope_granted=["openid", "email", "profile"],
                is_primary=True,
            )

            # Update user info if needed
            await self.user_repo.update_user(
                existing_user.id,
                profile_image_url=profile_image_url or existing_user.profile_image_url,
                email_verified=email_verified or existing_user.email_verified,
            )

            return existing_user, social_account, False

        # Create new user
        user = await self.user_repo.create_user(
            email=email,
            name=name,
            profile_image_url=profile_image_url,
            user_level=UserLevel.NORMAL.value,
            email_verified=email_verified,
        )

        # Create social account
        social_account = await self.social_account_repo.create_social_account(
            user_id=user.id,
            provider="google",
            provider_user_id=provider_user_id,
            provider_data=provider_data,
            scope_granted=["openid", "email", "profile"],
            is_primary=True,
        )

        logger.info(f"New user created: {user.email} (ID: {user.id})")

        return user, social_account, is_new_user

    async def get_user_by_id(self, user_id: uuid.UUID) -> User:
        """Get user by ID."""
        user = await self.user_repo.get_user_by_id(user_id)
        if not user:
            raise NotFound(message="User not found")
        return user

    async def get_user_by_email(self, email: str) -> User:
        """Get user by email."""
        user = await self.user_repo.get_user_by_email(email)
        if not user:
            raise NotFound(message="User not found")
        return user

    async def get_user_with_social_accounts(self, user_id: uuid.UUID) -> User:
        """Get user with all social accounts."""
        user = await self.user_repo.get_user_with_social_accounts(user_id)
        if not user:
            raise NotFound(message="User not found")
        return user

    async def update_user_profile(
        self,
        user_id: uuid.UUID,
        name: Optional[str] = None,
        profile_image_url: Optional[str] = None,
    ) -> User:
        """Update user profile information."""
        # Verify user exists
        user = await self.get_user_by_id(user_id)

        # Build update data
        update_data = {}
        if name is not None:
            if not name.strip():
                raise BadRequest(message="Name cannot be empty")
            update_data["name"] = name.strip()

        if profile_image_url is not None:
            update_data["profile_image_url"] = profile_image_url

        if not update_data:
            return user

        updated_user = await self.user_repo.update_user(user_id, **update_data)
        if not updated_user:
            raise NotFound(message="User not found")

        logger.info(f"User profile updated: {user.email} (ID: {user_id})")

        return updated_user

    async def update_last_login(self, user_id: uuid.UUID) -> None:
        """Update user's last login timestamp."""
        await self.user_repo.update_last_login(user_id)

    async def deactivate_user(self, user_id: uuid.UUID) -> User:
        """Deactivate user account."""
        updated_user = await self.user_repo.update_user(user_id, is_active=False)
        if not updated_user:
            raise NotFound(message="User not found")

        # Clear user cache
        await auth_cache.clear_user_auth_data(user_id)

        logger.info(f"User deactivated: {updated_user.email} (ID: {user_id})")

        return updated_user

    async def activate_user(self, user_id: uuid.UUID) -> User:
        """Activate user account."""
        updated_user = await self.user_repo.update_user(user_id, is_active=True)
        if not updated_user:
            raise NotFound(message="User not found")

        logger.info(f"User activated: {updated_user.email} (ID: {user_id})")

        return updated_user

    async def delete_user(self, user_id: uuid.UUID) -> bool:
        """Delete user account permanently."""
        # Verify user exists
        user = await self.get_user_by_id(user_id)

        # Clear cache first
        await auth_cache.clear_user_auth_data(user_id)

        # Delete user (this will cascade delete social accounts due to foreign key)
        deleted = await self.user_repo.delete_user(user_id)

        if deleted:
            logger.info(f"User deleted: {user.email} (ID: {user_id})")

        return deleted

    async def get_user_social_accounts(
        self, user_id: uuid.UUID, provider: Optional[str] = None
    ) -> list[SocialAccount]:
        """Get user's social accounts."""
        # Verify user exists
        await self.get_user_by_id(user_id)

        return await self.social_account_repo.get_user_social_accounts(
            user_id, provider
        )

    async def disconnect_social_account(
        self, user_id: uuid.UUID, account_id: uuid.UUID
    ) -> bool:
        """Disconnect social account from user."""
        # Verify user exists
        await self.get_user_by_id(user_id)

        # Get social account
        social_account = await self.social_account_repo.get_social_account_by_id(
            account_id
        )
        if not social_account or social_account.user_id != user_id:
            raise NotFound(message="Social account not found")

        # Check if user has other social accounts or password (in future)
        user_social_accounts = await self.social_account_repo.get_user_social_accounts(
            user_id
        )
        if len(user_social_accounts) <= 1:
            raise BadRequest(message="Cannot disconnect the only authentication method")

        # Delete social account
        deleted = await self.social_account_repo.delete_social_account(account_id)

        if deleted:
            logger.info(
                f"Social account disconnected: {social_account.provider} for user {user_id}"
            )

        return deleted


# Global instance
user_service = UserService()
