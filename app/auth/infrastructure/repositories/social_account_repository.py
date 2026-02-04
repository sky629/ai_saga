"""Social Account Repository Implementation."""

from typing import Optional
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.application.ports import SocialAccountRepositoryInterface
from app.auth.domain.entities import SocialAccountEntity
from app.auth.domain.value_objects import AuthProvider
from app.auth.infrastructure.persistence.mappers import SocialAccountMapper
from app.auth.infrastructure.persistence.models.user_models import (
    SocialAccount as SocialAccountModel,
)


class SocialAccountRepositoryImpl(SocialAccountRepositoryInterface):
    """소셜 계정 저장소 구현체."""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_by_provider(
        self, provider: AuthProvider, provider_user_id: str
    ) -> Optional[SocialAccountEntity]:
        result = await self._db.execute(
            select(SocialAccountModel).where(
                SocialAccountModel.provider == provider.value,
                SocialAccountModel.provider_user_id == provider_user_id,
            )
        )
        orm = result.scalar_one_or_none()
        return SocialAccountMapper.to_entity(orm) if orm else None

    async def get_by_user(self, user_id: UUID) -> list[SocialAccountEntity]:
        result = await self._db.execute(
            select(SocialAccountModel).where(
                SocialAccountModel.user_id == user_id
            )
        )
        orms = result.scalars().all()
        return [SocialAccountMapper.to_entity(orm) for orm in orms]

    async def get_by_id(
        self, account_id: UUID
    ) -> Optional[SocialAccountEntity]:
        result = await self._db.execute(
            select(SocialAccountModel).where(
                SocialAccountModel.id == account_id
            )
        )
        orm = result.scalar_one_or_none()
        return SocialAccountMapper.to_entity(orm) if orm else None

    async def save(self, account: SocialAccountEntity) -> SocialAccountEntity:
        result = await self._db.execute(
            select(SocialAccountModel).where(
                SocialAccountModel.id == account.id
            )
        )
        orm = result.scalar_one_or_none()

        if orm is None:
            # Create
            orm = SocialAccountModel(
                id=account.id,
                user_id=account.user_id,
                provider=account.provider.value,
                provider_user_id=account.provider_user_id,
                provider_data=account.provider_data,
                scope_granted=account.scope_granted,
                is_primary=account.is_primary,
                connected_at=account.created_at,  # DB Model uses connected_at
                last_used_at=account.last_used_at,
            )
            self._db.add(orm)
        else:
            # Update
            orm.provider_data = account.provider_data
            orm.scope_granted = account.scope_granted
            orm.is_primary = account.is_primary
            orm.last_used_at = account.last_used_at
            # Other fields typically don't change or require explicit logic

        await self._db.commit()
        await self._db.refresh(orm)
        return SocialAccountMapper.to_entity(orm)

    async def delete(self, account_id: UUID) -> bool:
        result = await self._db.execute(
            delete(SocialAccountModel).where(
                SocialAccountModel.id == account_id
            )
        )
        await self._db.commit()
        return result.rowcount > 0
