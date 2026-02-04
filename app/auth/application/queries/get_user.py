"""Get User Query."""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.domain.entities import UserEntity
from app.auth.infrastructure.persistence.mappers import UserMapper
from app.auth.infrastructure.persistence.models.user_models import (
    User as UserModel,
)


class GetUserQuery:
    """사용자 조회 쿼리 (CQRS Read Only)."""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def execute(self, user_id: UUID) -> Optional[UserEntity]:
        """ID로 사용자 조회."""
        result = await self._db.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        orm = result.scalar_one_or_none()
        return UserMapper.to_entity(orm) if orm else None

    async def get_by_email(self, email: str) -> Optional[UserEntity]:
        """이메일로 사용자 조회."""
        result = await self._db.execute(
            select(UserModel).where(UserModel.email == email)
        )
        orm = result.scalar_one_or_none()
        return UserMapper.to_entity(orm) if orm else None
