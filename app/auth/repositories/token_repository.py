"""Token repository for JWT token management."""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from jose import JWTError, jwt

from app.auth.repositories.cache.auth_cache_repository import auth_cache
from app.common.exception import Unauthorized
from config.settings import settings


class TokenRepository:
    """Repository for JWT token operations."""

    def __init__(self):
        self.secret_key = settings.jwt_secret_key
        self.algorithm = settings.jwt_algorithm
        self.access_token_expire_minutes = settings.jwt_access_token_expire_minutes

    def create_access_token(
        self,
        user_id: uuid.UUID,
        email: str,
        user_level: int,
        expires_delta: Optional[timedelta] = None,
    ) -> Dict[str, Any]:
        """Create JWT access token."""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=self.access_token_expire_minutes
            )

        jti = str(uuid.uuid4())  # JWT ID for token tracking

        to_encode = {
            "sub": str(user_id),  # Subject (user ID)
            "email": email,
            "user_level": user_level,
            "exp": expire,  # Expiration time
            "iat": datetime.utcnow(),  # Issued at
            "jti": jti,  # JWT ID
            "type": "access",
        }

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

        return {
            "access_token": encoded_jwt,
            "token_type": "bearer",
            "expires_in": (
                int(expires_delta.total_seconds())
                if expires_delta
                else self.access_token_expire_minutes * 60
            ),
            "expires_at": expire,
            "jti": jti,
        }

    def create_refresh_token(
        self, user_id: uuid.UUID, expires_delta: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """Create JWT refresh token."""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=30)  # 30 days for refresh token

        jti = str(uuid.uuid4())

        to_encode = {
            "sub": str(user_id),
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": jti,
            "type": "refresh",
        }

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

        return {"refresh_token": encoded_jwt, "expires_at": expire, "jti": jti}

    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # Check if token is blacklisted
            jti = payload.get("jti")
            if jti and await auth_cache.is_jwt_token_blacklisted(jti):
                raise Unauthorized(message="Token has been revoked")

            return payload

        except JWTError:
            raise Unauthorized(message="Invalid token")

    async def blacklist_token(self, token: str) -> None:
        """Add token to blacklist."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            jti = payload.get("jti")
            exp = payload.get("exp")

            if jti and exp:
                # Calculate remaining time for the token
                expire_time = int(exp - datetime.utcnow().timestamp())
                if expire_time > 0:
                    await auth_cache.blacklist_jwt_token(jti, expire_time)

        except JWTError:
            # If token is invalid, no need to blacklist
            pass

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Create new access token from refresh token."""
        payload = await self.verify_token(refresh_token)

        # Verify it's a refresh token
        if payload.get("type") != "refresh":
            raise Unauthorized(message="Invalid refresh token")

        user_id = uuid.UUID(payload.get("sub"))

        # Get user info from cache or database
        session_data = await auth_cache.get_jwt_session(user_id)
        if not session_data:
            raise Unauthorized(message="Session expired")

        # Create new access token
        return self.create_access_token(
            user_id=user_id,
            email=session_data["email"],
            user_level=session_data["user_level"],
        )

    async def get_current_user_id(self, token: str) -> uuid.UUID:
        """Get current user ID from token."""
        payload = await self.verify_token(token)
        return uuid.UUID(payload.get("sub"))

    async def set_session(
        self, user_id: uuid.UUID, email: str, user_level: int, expires_in: int
    ) -> None:
        """Store user session in cache."""
        session_data = {
            "email": email,
            "user_level": user_level,
            "created_at": datetime.utcnow().isoformat(),
        }
        await auth_cache.set_jwt_session(user_id, session_data, expire=expires_in)

    async def clear_session(self, user_id: uuid.UUID) -> None:
        """Clear user session from cache."""
        await auth_cache.delete_jwt_session(user_id)


# Global instance
token_repository = TokenRepository()
