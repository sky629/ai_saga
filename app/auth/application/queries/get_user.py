"""Get User Query."""

from typing import Optional
from uuid import UUID

from app.auth.application.ports import UserRepositoryInterface
from app.auth.domain.entities import UserEntity


class GetUserQuery:
    """사용자 조회 쿼리 (CQRS Read Only)."""

    def __init__(self, user_repo: UserRepositoryInterface):
        self._user_repo = user_repo

    async def execute(self, user_id: UUID) -> Optional[UserEntity]:
        """ID로 사용자 조회."""
        return await self._user_repo.get_by_id(user_id)

    async def get_by_email(self, email: str) -> Optional[UserEntity]:
        """이메일로 사용자 조회."""
        return await self._user_repo.get_by_email(email)
