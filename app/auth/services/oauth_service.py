"""OAuth service for handling authentication flows."""

import uuid
from typing import Any, Dict, Tuple

from app.auth.models.postgres_models import User
from app.auth.repositories.cache.auth_cache_repository import auth_cache
from app.auth.repositories.token_repository import token_repository
from app.auth.representations.response import TokenResponse
from app.auth.services.google_oauth_service import google_oauth_service
from app.auth.services.user_service import user_service
from app.common.exception import BadRequest
from app.common.logging import logger
from app.common.storage.redis import CacheExpire


class OAuthService:
    """Service for OAuth authentication flows."""

    def __init__(self):
        self.google_oauth = google_oauth_service
        self.user_service = user_service
        self.token_repo = token_repository

    async def initiate_google_login(self) -> Dict[str, str]:
        """Initiate Google OAuth login flow."""
        auth_url, state = await self.google_oauth.generate_auth_url()

        return {"auth_url": auth_url, "state": state}

    async def handle_google_callback(
        self, code: str, state: str
    ) -> Tuple[User, TokenResponse, bool]:
        """Handle Google OAuth callback and create/login user."""

        # Verify state parameter for CSRF protection
        is_valid_state = await self.google_oauth.verify_state(state)
        if not is_valid_state:
            raise BadRequest(message="Invalid state parameter")

        # Exchange authorization code for tokens
        google_tokens = await self.google_oauth.exchange_code_for_tokens(code)
        access_token = google_tokens["access_token"]
        refresh_token = google_tokens.get("refresh_token")

        # Get user information from Google
        google_user_info = await self.google_oauth.get_user_info(access_token)

        # Create or get existing user
        user, social_account, is_new_user = (
            await self.user_service.create_user_from_google(
                google_user_info,
                {
                    "google_tokens": google_tokens,
                    "user_info": google_user_info,
                },
            )
        )

        # Update last login
        await self.user_service.update_last_login(user.id)

        # Set Google tokens in cache
        if refresh_token:
            await auth_cache.set_google_refresh_token(user.id, refresh_token)

        # Calculate token expiration
        expires_in = google_tokens.get("expires_in", 3600)  # Default 1 hour
        await auth_cache.set_google_access_token(
            user.id, access_token, expire=expires_in
        )

        # Create JWT tokens
        access_token_data = self.token_repo.create_access_token(
            user_id=user.id, email=user.email, user_level=user.user_level
        )

        refresh_token_data = self.token_repo.create_refresh_token(user.id)

        # Set session in cache
        await self.token_repo.set_session(
            user_id=user.id,
            email=user.email,
            user_level=user.user_level,
            expires_in=access_token_data["expires_in"],
        )

        # Create token response
        token_response = TokenResponse(
            access_token=access_token_data["access_token"],
            token_type=access_token_data["token_type"],
            expires_in=access_token_data["expires_in"],
            refresh_token=refresh_token_data["refresh_token"],
        )

        logger.info(
            f"User authenticated via Google: {user.email} (new_user: {is_new_user})"
        )

        return user, token_response, is_new_user

    async def refresh_jwt_token(self, refresh_token: str) -> TokenResponse:
        """Refresh JWT access token."""
        new_token_data = await self.token_repo.refresh_access_token(refresh_token)

        return TokenResponse(
            access_token=new_token_data["access_token"],
            token_type=new_token_data["token_type"],
            expires_in=new_token_data["expires_in"],
        )

    async def refresh_google_token(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """Refresh Google access token for a user."""
        # Get stored refresh token
        refresh_token = await auth_cache.get_google_refresh_token(user_id)
        if not refresh_token:
            raise BadRequest(message="No Google refresh token found")

        # Refresh the token
        new_tokens = await self.google_oauth.refresh_access_token(refresh_token)

        # Set new access token
        expires_in = new_tokens.get("expires_in", CacheExpire.HOUR)
        await auth_cache.set_google_access_token(
            user_id, new_tokens["access_token"], expire=expires_in
        )

        # Update refresh token if provided
        if "refresh_token" in new_tokens:
            await auth_cache.set_google_refresh_token(
                user_id, new_tokens["refresh_token"]
            )

        return new_tokens

    async def logout_user(self, user_id: uuid.UUID, access_token: str) -> None:
        """Logout user and cleanup tokens."""
        # Blacklist the current JWT token
        await self.token_repo.blacklist_token(access_token)

        # Clear user session
        await self.token_repo.clear_session(user_id)

        # Try to revoke Google tokens
        google_access_token = await auth_cache.get_google_access_token(user_id)
        if google_access_token:
            await self.google_oauth.revoke_token(google_access_token)

        google_refresh_token = await auth_cache.get_google_refresh_token(user_id)
        if google_refresh_token:
            await self.google_oauth.revoke_token(google_refresh_token)

        # Clear all cached auth data
        await auth_cache.clear_user_auth_data(user_id)

        logger.info(f"User logged out: {user_id}")

    async def get_current_user_from_token(self, token: str) -> User:
        """Get current user from JWT token."""
        user_id = await self.token_repo.get_current_user_id(token)
        return await self.user_service.get_user_by_id(user_id)

    async def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate JWT token and return payload."""
        return await self.token_repo.verify_token(token)


# Global instance
oauth_service = OAuthService()
