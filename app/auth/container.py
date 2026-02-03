"""Auth DI Container."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.application.queries.get_user import GetUserQuery
from app.auth.application.use_cases.create_user import CreateUserUseCase
from app.auth.infrastructure.repositories.social_account_repository import (
    SocialAccountRepositoryImpl,
)
from app.auth.infrastructure.repositories.user_repository import UserRepositoryImpl


class AuthContainer:
    """Auth 모듈 의존성 컨테이너."""

    def __init__(self, db: AsyncSession):
        self._db = db

    # === Repositories ===
    def user_repository(self):
        return UserRepositoryImpl(self._db)

    def social_account_repository(self):
        return SocialAccountRepositoryImpl(self._db)

    # === Use Cases (Commands - Write DB) ===
    def create_user_use_case(self) -> CreateUserUseCase:
        return CreateUserUseCase(
            user_repo=self.user_repository(),
            social_repo=self.social_account_repository(),
        )

    # === Queries (Read DB) ===
    def get_user_query(self) -> GetUserQuery:
        return GetUserQuery(self._db)
