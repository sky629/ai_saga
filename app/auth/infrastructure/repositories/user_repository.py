"""User Repository Implementation."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.application.ports import UserRepositoryInterface
from app.auth.domain.entities import UserEntity
from app.auth.domain.value_objects import UserLevel
from app.auth.infrastructure.persistence.mappers import UserMapper
from app.auth.infrastructure.persistence.models.postgres_models import User as UserModel


class UserRepositoryImpl(UserRepositoryInterface):
    """사용자 저장소 구현체."""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_by_id(self, user_id: UUID) -> Optional[UserEntity]:
        result = await self._db.execute(select(UserModel).where(UserModel.id == user_id))
        orm = result.scalar_one_or_none()
        return UserMapper.to_entity(orm) if orm else None

    async def get_by_email(self, email: str) -> Optional[UserEntity]:
        result = await self._db.execute(select(UserModel).where(UserModel.email == email))
        orm = result.scalar_one_or_none()
        return UserMapper.to_entity(orm) if orm else None

    async def save(self, user: UserEntity) -> UserEntity:
        result = await self._db.execute(select(UserModel).where(UserModel.id == user.id))
        orm = result.scalar_one_or_none()

        if orm is None:
            # Create
            orm = UserModel(
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
            )
            self._db.add(orm)
        else:
            # Update
            updates = UserMapper.to_dict(user)
            for key, value in updates.items():
                setattr(orm, key, value)

        await self._db.commit()
        await self._db.refresh(orm)
        return UserMapper.to_entity(orm)

    async def update_last_login(self, user_id: UUID, login_at: datetime) -> None:
        stmt = (
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(last_login_at=login_at)
        )
        await self._db.execute(stmt)
        await self._db.commit()
