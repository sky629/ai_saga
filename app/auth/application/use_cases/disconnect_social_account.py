"""Disconnect Social Account Use Case."""

from uuid import UUID

from app.auth.application.ports import (
    SocialAccountRepositoryInterface,
    UserRepositoryInterface,
)
from app.common.exception import BadRequest, NotFound


class DisconnectSocialAccountUseCase:
    """소셜 계정 연결 해제 유스케이스."""

    def __init__(
        self,
        social_repo: SocialAccountRepositoryInterface,
        user_repo: UserRepositoryInterface,
    ):
        self._social_repo = social_repo
        self._user_repo = user_repo

    async def execute(self, user_id: UUID, account_id: UUID) -> bool:
        # 1. Verify user exists (Optional, ensures user is valid)
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise NotFound(message="User not found")

        # 2. Get social account
        account = await self._social_repo.get_by_id(account_id)
        if not account or account.user_id != user_id:
            raise NotFound(message="Social account not found")

        # 3. Check if user has other authentication methods
        # For now, we only check social accounts. In future, check for password too.
        user_accounts = await self._social_repo.get_by_user(user_id)
        if len(user_accounts) <= 1:
            raise BadRequest(
                message="Cannot disconnect the only authentication method"
            )

        # 4. Delete
        return await self._social_repo.delete(account_id)
