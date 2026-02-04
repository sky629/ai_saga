"""Auth Dependencies."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
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
from app.auth.container import AuthContainer
from app.auth.domain.entities.user import UserEntity
from app.common.storage.postgres import postgres_storage

security = HTTPBearer()


def get_auth_container(
    db: Annotated[AsyncSession, Depends(postgres_storage.write_db)],
) -> AuthContainer:
    """Auth Container (Write DB)."""
    return AuthContainer(db)


def get_read_auth_container(
    db: Annotated[AsyncSession, Depends(postgres_storage.read_db)],
) -> AuthContainer:
    """Auth Container (Read DB)."""
    return AuthContainer(db)


# === Commands ===
def get_handle_oauth_callback_use_case(
    container: Annotated[AuthContainer, Depends(get_auth_container)],
) -> HandleOAuthCallbackUseCase:
    return container.handle_oauth_callback_use_case()


def get_update_user_profile_use_case(
    container: Annotated[AuthContainer, Depends(get_auth_container)],
) -> UpdateUserProfileUseCase:
    return container.update_user_profile_use_case()


def get_logout_use_case(
    container: Annotated[AuthContainer, Depends(get_auth_container)],
) -> LogoutUseCase:
    return container.logout_use_case()


def get_refresh_token_use_case(
    container: Annotated[AuthContainer, Depends(get_auth_container)],
) -> RefreshTokenUseCase:
    return container.refresh_token_use_case()


def get_refresh_google_token_use_case(
    container: Annotated[AuthContainer, Depends(get_auth_container)],
) -> RefreshGoogleTokenUseCase:
    return container.refresh_google_token_use_case()


def get_disconnect_social_account_use_case(
    container: Annotated[AuthContainer, Depends(get_auth_container)],
) -> DisconnectSocialAccountUseCase:
    return container.disconnect_social_account_use_case()


# === Queries ===
def get_user_query(
    container: Annotated[AuthContainer, Depends(get_read_auth_container)],
) -> GetUserQuery:
    return container.get_user_query()


def get_social_accounts_query(
    container: Annotated[AuthContainer, Depends(get_read_auth_container)],
) -> GetSocialAccountsQuery:
    return container.get_social_accounts_query()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    container: AuthContainer = Depends(get_read_auth_container),
) -> UserEntity:
    """Validate token and return current user."""
    token = credentials.credentials
    token_service = container.token_service()
    user_repo = container.user_repository()

    try:
        payload = await token_service.verify_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await user_repo.get_by_id(UUID(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


# === Type Aliases ===
HandleOAuthCallbackDep = Annotated[
    HandleOAuthCallbackUseCase, Depends(get_handle_oauth_callback_use_case)
]
UpdateUserProfileDep = Annotated[
    UpdateUserProfileUseCase, Depends(get_update_user_profile_use_case)
]
LogoutDep = Annotated[LogoutUseCase, Depends(get_logout_use_case)]
RefreshTokenDep = Annotated[
    RefreshTokenUseCase, Depends(get_refresh_token_use_case)
]
RefreshGoogleTokenDep = Annotated[
    RefreshGoogleTokenUseCase, Depends(get_refresh_google_token_use_case)
]
DisconnectSocialAccountDep = Annotated[
    DisconnectSocialAccountUseCase,
    Depends(get_disconnect_social_account_use_case),
]
GetUserDep = Annotated[GetUserQuery, Depends(get_user_query)]
GetSocialAccountsDep = Annotated[
    GetSocialAccountsQuery, Depends(get_social_accounts_query)
]
