"""Token Service Adapter Implementation."""

from datetime import timedelta
from typing import Any, Dict, Optional
from uuid import UUID

from jose import JWTError, jwt
from uuid_utils import uuid7

from app.auth.application.ports import (
    AuthCacheInterface,
    TokenServiceInterface,
)
from app.common.exception import Unauthorized
from app.common.utils.datetime import get_utc_datetime
from config.settings import settings


class TokenAdapter(TokenServiceInterface):
    """JWT 토큰 서비스 어댑터."""

    def __init__(self, cache: AuthCacheInterface):
        self._cache = cache
        self.secret_key = settings.jwt_secret_key
        self.algorithm = settings.jwt_algorithm
        self.access_token_expire_minutes = (
            settings.jwt_access_token_expire_minutes
        )

    def create_access_token(
        self,
        user_id: UUID,
        email: str,
        user_level: int,
        expires_delta: Optional[timedelta] = None,
    ) -> Dict[str, Any]:
        if expires_delta:
            expire = get_utc_datetime() + expires_delta
        else:
            expire = get_utc_datetime() + timedelta(
                minutes=self.access_token_expire_minutes
            )

        jti = str(uuid7())

        to_encode = {
            "sub": str(user_id),
            "email": email,
            "user_level": user_level,
            "exp": expire,
            "iat": get_utc_datetime(),
            "jti": jti,
            "type": "access",
        }

        encoded_jwt = jwt.encode(
            to_encode, self.secret_key, algorithm=self.algorithm
        )

        return {
            "access_token": encoded_jwt,
            "token_type": "bearer",
            "expires_in": (
                int(expires_delta.total_seconds())
                if expires_delta
                else self.access_token_expire_minutes * 60
            ),
            "jti": jti,
        }

    def create_refresh_token(
        self, user_id: UUID, expires_delta: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        if expires_delta:
            expire = get_utc_datetime() + expires_delta
        else:
            expire = get_utc_datetime() + timedelta(days=30)

        jti = str(uuid7())

        to_encode = {
            "sub": str(user_id),
            "exp": expire,
            "iat": get_utc_datetime(),
            "jti": jti,
            "type": "refresh",
        }

        encoded_jwt = jwt.encode(
            to_encode, self.secret_key, algorithm=self.algorithm
        )

        return {"refresh_token": encoded_jwt, "jti": jti}

    async def verify_token(self, token: str) -> Dict[str, Any]:
        try:
            payload = jwt.decode(
                token, self.secret_key, algorithms=[self.algorithm]
            )
            jti = payload.get("jti")
            if jti and await self._cache.is_jwt_token_blacklisted(jti):
                raise Unauthorized(message="Token has been revoked")
            return payload
        except JWTError:
            raise Unauthorized(message="Invalid token")

    async def blacklist_token(self, token: str) -> None:
        try:
            payload = jwt.decode(
                token, self.secret_key, algorithms=[self.algorithm]
            )
            jti = payload.get("jti")
            exp = payload.get("exp")

            if jti and exp:
                expire_time = int(exp - get_utc_datetime().timestamp())
                if expire_time > 0:
                    await self._cache.blacklist_jwt_token(jti, expire_time)
        except JWTError:
            pass
