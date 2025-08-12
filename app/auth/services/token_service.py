"""Token service for JWT management and authentication middleware."""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth import logger
from app.auth.models.postgres_models import User
from app.auth.services.oauth_service import oauth_service
from app.common.exception import Unauthorized

# Security scheme for API documentation
security = HTTPBearer()


class TokenService:
    """Service for token validation and authentication."""

    async def get_current_user(
        self, credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> User:
        """Get current authenticated user from JWT token."""
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            user = await oauth_service.get_current_user_from_token(
                credentials.credentials
            )

            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User account is deactivated",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            return user

        except Unauthorized as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as e:
            logger.exception(e)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    async def get_current_active_user(
        self, current_user: User = Depends(lambda self: self.get_current_user)
    ) -> User:
        """Get current active user (same as get_current_user but explicit)."""
        return current_user

    async def get_current_admin_user(
        self, current_user: User = Depends(lambda self: self.get_current_user)
    ) -> User:
        """Get current user if they are admin."""
        from app.common.enums.user_level import UserLevel

        if not UserLevel.is_admin(current_user.user_level):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )

        return current_user

    async def get_optional_current_user(
        self,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    ) -> Optional[User]:
        """Get current user if token is provided, otherwise return None."""
        if not credentials:
            return None

        try:
            return await oauth_service.get_current_user_from_token(
                credentials.credentials
            )
        except Exception as e:
            logger.warning(e)
            return None

    async def validate_token_payload(self, token: str) -> dict:
        """Validate token and return payload without getting user."""
        return await oauth_service.validate_token(token)


# Global instance
token_service = TokenService()


# Dependency functions for FastAPI
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """FastAPI dependency to get current authenticated user."""
    return await token_service.get_current_user(credentials)


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """FastAPI dependency to get current admin user."""
    return await token_service.get_current_admin_user(current_user)


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[User]:
    """FastAPI dependency to get optional current user."""
    return await token_service.get_optional_current_user(credentials)
