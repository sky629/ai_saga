"""Google OAuth service implementation."""

import secrets
from typing import Any, Dict, Tuple
from urllib.parse import urlencode

import httpx

from app.auth.repositories.cache.auth_cache_repository import auth_cache
from app.common.exception import BadRequest, ServerError
from app.common.logging import logger
from app.common.storage.redis import CacheExpire
from app.common.utils.datetime import get_utc_timestamp
from config.settings import settings


class GoogleOAuthService:
    """Google OAuth 2.0 service implementation."""

    def __init__(self):
        self.client_id = settings.google_client_id
        self.client_secret = settings.google_client_secret
        self.redirect_uri = settings.google_redirect_uri

        # Google OAuth endpoints
        self.auth_endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_endpoint = "https://oauth2.googleapis.com/token"
        self.userinfo_endpoint = "https://www.googleapis.com/oauth2/v2/userinfo"

        # OAuth scopes
        self.scopes = ["openid", "email", "profile"]

    async def generate_auth_url(self) -> Tuple[str, str]:
        """Generate Google OAuth authorization URL with state parameter."""
        # Generate secure random state for CSRF protection
        state = secrets.token_urlsafe(32)

        # Set state in cache for verification
        state_data = {
            "created_at": get_utc_timestamp(),  # Just a timestamp placeholder
            "provider": "google",
        }
        await auth_cache.set_oauth_state(
            state, state_data, expire=CacheExpire.MINUTE * 10
        )  # 1 minutes

        # Build authorization URL
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes),
            "response_type": "code",
            "state": state,
            "access_type": "offline",  # Request refresh token
            "prompt": "consent",  # Force consent screen to get refresh token
        }

        auth_url = f"{self.auth_endpoint}?{urlencode(params)}"

        return auth_url, state

    async def verify_state(self, state: str) -> bool:
        """Verify OAuth state parameter."""
        state_data = await auth_cache.get_oauth_state(state)
        if not state_data:
            return False

        # Clean up state after verification
        await auth_cache.delete_oauth_state(state)
        return True

    async def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access and refresh tokens."""
        token_data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.token_endpoint,
                    data=token_data,
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()

                tokens = response.json()

                # Validate required fields
                if "access_token" not in tokens:
                    raise BadRequest(
                        message="Failed to obtain access token from Google"
                    )

                return tokens

            except httpx.HTTPStatusError as e:
                logger.error(f"Google token exchange failed: {e.response.text}")
                raise BadRequest(message="Failed to exchange authorization code")
            except Exception as e:
                logger.error(f"Google token exchange error: {str(e)}")
                raise ServerError(message="OAuth token exchange failed")

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from Google using access token."""
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.userinfo_endpoint, headers=headers)
                response.raise_for_status()

                user_info = response.json()

                # Validate required fields
                if "email" not in user_info:
                    raise BadRequest(message="Email not provided by Google")

                return user_info

            except httpx.HTTPStatusError as e:
                logger.error(f"Google user info request failed: {e.response.text}")
                raise BadRequest(message="Failed to fetch user information from Google")
            except Exception as e:
                logger.error(f"Google user info error: {str(e)}")
                raise ServerError(message="Failed to fetch user information")

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh Google access token using refresh token."""
        token_data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.token_endpoint,
                    data=token_data,
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()

                tokens = response.json()

                if "access_token" not in tokens:
                    raise BadRequest(message="Failed to refresh Google access token")

                return tokens

            except httpx.HTTPStatusError as e:
                logger.error(f"Google token refresh failed: {e.response.text}")
                raise BadRequest(message="Failed to refresh Google access token")
            except Exception as e:
                logger.error(f"Google token refresh error: {str(e)}")
                raise ServerError(message="Token refresh failed")

    async def revoke_token(self, token: str) -> bool:
        """Revoke Google access or refresh token."""
        revoke_url = f"https://oauth2.googleapis.com/revoke?token={token}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(revoke_url)
                return response.status_code == 200
            except Exception as e:
                logger.error(f"Google token revocation error: {str(e)}")
                return False


# Global instance
google_oauth_service = GoogleOAuthService()
