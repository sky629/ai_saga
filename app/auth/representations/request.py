"""Request models for authentication."""

from typing import Optional

from pydantic import BaseModel, Field


class GoogleCallbackRequest(BaseModel):
    """Google OAuth callback request model."""

    code: str = Field(..., description="Google OAuth authorization code")
    state: str = Field(..., description="CSRF protection state parameter")


class RefreshTokenRequest(BaseModel):
    """JWT token refresh request model."""

    refresh_token: str = Field(..., description="JWT refresh token")


class GoogleTokenRefreshRequest(BaseModel):
    """Google token refresh request model."""

    refresh_token: Optional[str] = Field(None, description="Google refresh token")


class UserUpdateRequest(BaseModel):
    """User profile update request model."""

    name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="User display name"
    )
    profile_image_url: Optional[str] = Field(None, description="Profile image URL")
