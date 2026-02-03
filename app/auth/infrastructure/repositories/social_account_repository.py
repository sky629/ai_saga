"""Social Account Repository Implementation."""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.application.ports import SocialAccountRepositoryInterface
from app.auth.domain.entities import SocialAccountEntity
from app.auth.domain.value_objects import AuthProvider
from app.auth.infrastructure.persistence.mappers import SocialAccountMapper
from app.auth.infrastructure.persistence.models.postgres_models import (
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
            select(SocialAccountModel).where(SocialAccountModel.user_id == user_id)
        )
        orms = result.scalars().all()
        return [SocialAccountMapper.to_entity(orm) for orm in orms]

    async def save(self, account: SocialAccountEntity) -> SocialAccountEntity:
        result = await self._db.execute(
            select(SocialAccountModel).where(SocialAccountModel.id == account.id)
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
                access_token=account.access_token,
                refresh_token=account.refresh_token,
                token_expires_at=account.token_expires_at,
                created_at=account.created_at,
                updated_at=account.updated_at,
                last_used_at=account.last_used_at,
                scope_granted=[], # TODO: Entity에 추가하거나 기본값 처리
                is_primary=False, # TODO: Entity에 추가하거나 기본값 처리
            )
            self._db.add(orm)
        else:
            # Update
            updates = SocialAccountMapper.to_dict(account)
            for key, value in updates.items():
                setattr(orm, key, value)

        await self._db.commit()
        await self._db.refresh(orm)
        return SocialAccountMapper.to_entity(orm)
