"""Auth DI Container."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.application.queries.get_social_accounts import (
    GetSocialAccountsQuery,
)
from app.auth.application.queries.get_user import GetUserQuery
from app.auth.application.use_cases.disconnect_social_account import (
    DisconnectSocialAccountUseCase,
)
from app.auth.application.use_cases.handle_oauth_callback import (
    HandleOAuthCallbackUseCase,
)
from app.auth.application.use_cases.logout import LogoutUseCase
from app.auth.application.use_cases.refresh_google_token import (
    RefreshGoogleTokenUseCase,
)
from app.auth.application.use_cases.refresh_token import RefreshTokenUseCase
from app.auth.application.use_cases.update_user_profile import (
    UpdateUserProfileUseCase,
)
from app.auth.infrastructure.adapters.auth_cache_adapter import (
    AuthCacheAdapter,
)
from app.auth.infrastructure.adapters.google_auth_adapter import (
    GoogleAuthAdapter,
)
from app.auth.infrastructure.adapters.token_adapter import TokenAdapter
from app.auth.infrastructure.repositories.social_account_repository import (
    SocialAccountRepositoryImpl,
)
from app.auth.infrastructure.repositories.user_repository import (
    UserRepositoryImpl,
)


class AuthContainer:
    """Auth 모듈 의존성 컨테이너."""

    def __init__(self, db: AsyncSession):
        self._db = db

    def user_repository(self):
        return UserRepositoryImpl(self._db)

    def social_repo(self):
        return SocialAccountRepositoryImpl(self._db)

    def cache_adapter(self):
        return AuthCacheAdapter()

    def token_service(self):
        return TokenAdapter(self.cache_adapter())

    def google_auth_adapter(self):
        return GoogleAuthAdapter(self.cache_adapter())

    def handle_oauth_callback_use_case(self) -> HandleOAuthCallbackUseCase:
        return HandleOAuthCallbackUseCase(
            user_repo=self.user_repository(),
            social_repo=self.social_repo(),
            oauth_provider=self.google_auth_adapter(),
            token_service=self.token_service(),
            cache=self.cache_adapter(),
        )

    def update_user_profile_use_case(self) -> UpdateUserProfileUseCase:
        return UpdateUserProfileUseCase(user_repo=self.user_repository())

    def logout_use_case(self) -> LogoutUseCase:
        return LogoutUseCase(
            token_service=self.token_service(), cache=self.cache_adapter()
        )

    def refresh_token_use_case(self) -> RefreshTokenUseCase:
        return RefreshTokenUseCase(
            token_service=self.token_service(), cache=self.cache_adapter()
        )

    def refresh_google_token_use_case(self) -> RefreshGoogleTokenUseCase:
        return RefreshGoogleTokenUseCase(
            oauth_provider=self.google_auth_adapter(),
            cache=self.cache_adapter(),
        )

    def disconnect_social_account_use_case(
        self,
    ) -> DisconnectSocialAccountUseCase:
        return DisconnectSocialAccountUseCase(
            social_repo=self.social_repo(),
            user_repo=self.user_repository(),
        )

    def get_user_query(self) -> GetUserQuery:
        return GetUserQuery(self._db)

    def get_social_accounts_query(self) -> GetSocialAccountsQuery:
        return GetSocialAccountsQuery(self.social_repo())
