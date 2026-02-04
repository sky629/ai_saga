"""Get Social Accounts Query."""

from typing import List, Optional
from uuid import UUID

from app.auth.application.ports import SocialAccountRepositoryInterface
from app.auth.domain.entities import SocialAccountEntity


class GetSocialAccountsQuery:
    """사용자 소셜 계정 조회 쿼리."""

    def __init__(self, social_repo: SocialAccountRepositoryInterface):
        self._social_repo = social_repo

    async def execute(
        self, user_id: UUID, provider: Optional[str] = None
    ) -> List[SocialAccountEntity]:
        accounts = await self._social_repo.get_by_user(user_id)
        if provider:
            return [
                account
                for account in accounts
                if account.provider.value == provider
            ]
        return accounts
