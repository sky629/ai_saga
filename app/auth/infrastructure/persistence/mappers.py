"""Auth ORM Mappers.

Domain Entity ↔ SQLAlchemy ORM Model 변환을 담당합니다.
"""

from app.auth.domain.entities import SocialAccountEntity, UserEntity
from app.auth.domain.value_objects import AuthProvider, UserLevel
from app.auth.infrastructure.persistence.models.user_models import (
    SocialAccount as SocialAccountModel,
)
from app.auth.infrastructure.persistence.models.user_models import (
    User as UserModel,
)


class UserMapper:
    """User Entity ↔ ORM Mappers."""

    @staticmethod
    def to_entity(orm: UserModel) -> UserEntity:
        return UserEntity(
            id=orm.id,
            email=orm.email,
            name=orm.name,
            profile_image_url=orm.profile_image_url,
            user_level=UserLevel(orm.user_level),
            is_active=orm.is_active,
            email_verified=orm.email_verified,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            last_login_at=orm.last_login_at,
        )

    @staticmethod
    def to_dict(entity: UserEntity) -> dict:
        """업데이트용 딕셔너리 반환."""
        return {
            "name": entity.name,
            "profile_image_url": entity.profile_image_url,
            "user_level": entity.user_level.value,
            "is_active": entity.is_active,
            "email_verified": entity.email_verified,
            "updated_at": entity.updated_at,
            "last_login_at": entity.last_login_at,
        }


class SocialAccountMapper:
    """SocialAccount Entity ↔ ORM Mappers."""

    @staticmethod
    def to_entity(orm: SocialAccountModel) -> SocialAccountEntity:
        return SocialAccountEntity(
            id=orm.id,
            user_id=orm.user_id,
            provider=AuthProvider(orm.provider),
            provider_user_id=orm.provider_user_id,
            provider_data=orm.provider_data,
            # Tokens are not stored in DB, so they are None when retrieving from DB
            access_token=None,
            refresh_token=None,
            token_expires_at=None,
            created_at=orm.connected_at,
            updated_at=orm.connected_at,
            last_used_at=orm.last_used_at,
        )

    @staticmethod
    def to_dict(entity: SocialAccountEntity) -> dict:
        return {
            "provider_data": entity.provider_data,
            "access_token": entity.access_token,
            "refresh_token": entity.refresh_token,
            "token_expires_at": entity.token_expires_at,
            "updated_at": entity.updated_at,
            "last_used_at": entity.last_used_at,
        }
