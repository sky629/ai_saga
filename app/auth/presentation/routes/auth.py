import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.routing import APIRoute

from app.auth import logger
from app.auth.infrastructure.persistence.models.postgres_models import User
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
from app.auth.services.oauth_service import oauth_service
from app.auth.services.token_service import get_current_user
from app.auth.services.user_service import user_service
from app.common.exception import APIException
from app.common.middleware.rate_limiting import RATE_LIMITS, limiter

auth_public_router_v1 = APIRouter(
    route_class=APIRoute,
    prefix="/api/v1/auth",
    tags=["auth"],
)


@auth_public_router_v1.get("/google/login/", response_model=GoogleLoginResponse)
@limiter.limit(RATE_LIMITS["oauth"])
async def google_login(request: Request):
    """Initialize Google OAuth login flow."""
    try:
        result = await oauth_service.initiate_google_login()
        return GoogleLoginResponse(auth_url=result["auth_url"], state=result["state"])
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
    callback_request: GoogleCallbackRequest = Depends(GoogleCallbackRequest),
):
    """Handle Google OAuth callback and authenticate user."""
    try:
        print(callback_request.code)
        print(callback_request.state)

        user, tokens, is_new_user = await oauth_service.handle_google_callback(
            callback_request.code, callback_request.state
        )

        print(user)
        print(tokens)
        print(is_new_user)

        return LoginResponse(
            user=UserResponse.model_validate(user),
            tokens=tokens,
            is_new_user=is_new_user,
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
async def refresh_token(token_request: RefreshTokenRequest, request: Request):
    """Refresh JWT access token using refresh token."""
    try:
        new_tokens = await oauth_service.refresh_jwt_token(token_request.refresh_token)
        return new_tokens
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
    current_user: User = Depends(get_current_user),
):
    """Refresh Google access token for current user."""
    try:
        new_tokens = await oauth_service.refresh_google_token(current_user.id)
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
    current_user: User = Depends(get_current_user),
    authorization: Optional[str] = Header(None),
):
    """Logout current user and invalidate tokens."""
    try:
        # Extract token from Authorization header
        token = None
        if authorization and authorization.startswith("Bearer "):
            token = authorization.split(" ")[1]

        if token:
            await oauth_service.logout_user(current_user.id, token)

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
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Update current user profile information."""
    try:
        updated_user = await user_service.update_user_profile(
            current_user.id,
            name=update_request.name,
            profile_image_url=update_request.profile_image_url,
        )
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
    current_user: User = Depends(get_current_user),
    provider: Optional[str] = None,
):
    """Get current user's connected social accounts."""
    try:
        social_accounts = await user_service.get_user_social_accounts(
            current_user.id, provider
        )

        return [
            SocialAccountResponse.model_validate(account) for account in social_accounts
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
    account_id: str, current_user: User = Depends(get_current_user)
):
    """Disconnect a social account from current user."""
    try:
        account_uuid = uuid.UUID(account_id)

        success = await user_service.disconnect_social_account(
            current_user.id, account_uuid
        )

        if success:
            return MessageResponse(message="Social account disconnected successfully")
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


@auth_public_router_v1.delete("/self/", response_model=MessageResponse)
async def delete_current_user(current_user: User = Depends(get_current_user)):
    """Delete current user account permanently."""
    try:
        success = await user_service.delete_user(current_user.id)

        if success:
            return MessageResponse(message="User account deleted successfully")
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete user account",
            )
    except APIException:
        raise
    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account deletion failed",
        )
