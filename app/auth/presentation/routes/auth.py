from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.routing import APIRoute

from app.auth import logger
from app.auth.application.use_cases.handle_oauth_callback import (
    OAuthCallbackInput,
)
from app.auth.application.use_cases.logout import LogoutInput
from app.auth.application.use_cases.refresh_token import RefreshTokenInput
from app.auth.application.use_cases.update_user_profile import (
    UpdateUserProfileInput,
)
from app.auth.dependencies import (
    DisconnectSocialAccountDep,
    GetSocialAccountsDep,
    HandleOAuthCallbackDep,
    LogoutDep,
    RefreshGoogleTokenDep,
    RefreshTokenDep,
    UpdateUserProfileDep,
    get_auth_container,
    get_current_user,
)
from app.auth.domain.value_objects import AuthProvider
from app.auth.infrastructure.persistence.models.user_models import User
from app.auth.presentation.routes.schemas.request import (
    GoogleCallbackRequest,
    GoogleTokenRefreshRequest,
    RefreshTokenRequest,
    UserUpdateRequest,
)
from app.auth.presentation.routes.schemas.response import (
    GoogleLoginResponse,
    LoginResponse,
    MessageResponse,
    SocialAccountResponse,
    TokenResponse,
    UserResponse,
)
from app.common.exception import APIException
from app.common.middleware.rate_limiting import RATE_LIMITS, limiter

auth_public_router_v1 = APIRouter(
    route_class=APIRoute,
    prefix="/api/v1/auth",
    tags=["auth"],
)


@auth_public_router_v1.get(
    "/google/login/", response_model=GoogleLoginResponse
)
@limiter.limit(RATE_LIMITS["oauth"])
async def google_login(
    request: Request, container=Depends(get_auth_container)
):
    """Initialize Google OAuth login flow."""
    try:
        oauth_provider = container.google_auth_adapter()
        auth_url, state = await oauth_provider.generate_auth_url()
        return GoogleLoginResponse(auth_url=auth_url, state=state)
    except APIException:
        raise
    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate Google login",
        )


@auth_public_router_v1.get("/google/callback/", response_model=LoginResponse)
@limiter.limit(RATE_LIMITS["oauth"])
async def google_callback(
    request: Request,
    use_case: HandleOAuthCallbackDep,
    callback_request: GoogleCallbackRequest = Depends(GoogleCallbackRequest),
):
    """Handle Google OAuth callback and authenticate user."""
    try:
        input_data = OAuthCallbackInput(
            code=callback_request.code,
            state=callback_request.state,
            provider=AuthProvider.GOOGLE,
        )
        result = await use_case.execute(input_data)

        return LoginResponse(
            user=UserResponse.model_validate(result.user),
            tokens=TokenResponse(
                access_token=result.access_token,
                refresh_token=result.refresh_token,
                expires_in=result.expires_in,
            ),
            is_new_user=result.is_new_user,
        )
    except APIException:
        raise
    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed",
        )


@auth_public_router_v1.post("/refresh/", response_model=TokenResponse)
@limiter.limit(RATE_LIMITS["auth"])
async def refresh_token(
    token_request: RefreshTokenRequest,
    use_case: RefreshTokenDep,
    request: Request,
):
    """Refresh JWT access token using refresh token."""
    try:
        input_data = RefreshTokenInput(
            refresh_token=token_request.refresh_token
        )
        result = await use_case.execute(input_data)
        return TokenResponse(
            access_token=result.access_token,
            token_type=result.token_type,
            expires_in=result.expires_in,
        )
    except APIException:
        raise
    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed",
        )


@auth_public_router_v1.post("/google/refresh/", response_model=dict)
async def refresh_google_token(
    request: GoogleTokenRefreshRequest,
    use_case: RefreshGoogleTokenDep,
    current_user: User = Depends(get_current_user),
):
    """Refresh Google access token for current user."""
    try:
        new_tokens = await use_case.execute(current_user.id)
        return {
            "message": "Google token refreshed successfully",
            "expires_in": new_tokens.get("expires_in"),
        }
    except APIException:
        raise
    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google token refresh failed",
        )


@auth_public_router_v1.post("/logout/", response_model=MessageResponse)
async def logout(
    use_case: LogoutDep,
    current_user: User = Depends(get_current_user),
    authorization: Optional[str] = Header(None),
):
    """Logout current user and invalidate tokens."""
    try:
        token = None
        if authorization and authorization.startswith("Bearer "):
            token = authorization.split(" ")[1]

        if token:
            input_data = LogoutInput(
                user_id=current_user.id, access_token=token
            )
            await use_case.execute(input_data)

        return MessageResponse(message="Successfully logged out")
    except APIException:
        raise
    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed",
        )


@auth_public_router_v1.get("/self/", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """Get current authenticated user information."""
    return UserResponse.model_validate(current_user)


@auth_public_router_v1.put("/self/", response_model=UserResponse)
@limiter.limit(RATE_LIMITS["user_update"])
async def update_current_user(
    update_request: UserUpdateRequest,
    use_case: UpdateUserProfileDep,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Update current user profile information."""
    try:
        input_data = UpdateUserProfileInput(
            name=update_request.name,
            profile_image_url=update_request.profile_image_url,
        )
        updated_user = await use_case.execute(current_user.id, input_data)
        return UserResponse.model_validate(updated_user)
    except APIException:
        raise
    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile update failed",
        )


@auth_public_router_v1.get(
    "/self/social-accounts/", response_model=List[SocialAccountResponse]
)
async def get_user_social_accounts(
    query: GetSocialAccountsDep,
    current_user: User = Depends(get_current_user),
    provider: Optional[str] = None,
):
    """Get current user's connected social accounts."""
    try:
        social_accounts = await query.execute(current_user.id, provider)

        return [
            SocialAccountResponse.model_validate(account)
            for account in social_accounts
        ]
    except APIException:
        raise
    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch social accounts",
        )


@auth_public_router_v1.delete(
    "/self/social-accounts/{account_id}/", response_model=MessageResponse
)
async def disconnect_social_account(
    account_id: str,
    use_case: DisconnectSocialAccountDep,
    current_user: User = Depends(get_current_user),
):
    """Disconnect a social account from current user."""
    try:
        account_uuid = UUID(account_id)

        success = await use_case.execute(current_user.id, account_uuid)

        if success:
            return MessageResponse(
                message="Social account disconnected successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Social account not found",
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid account ID format",
        )
    except APIException:
        raise
    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disconnect social account",
        )
