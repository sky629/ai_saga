"""Response models for authentication."""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class UserResponse(BaseModel):
    """User response model."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: str
    user_level: int
    profile_image_url: Optional[str] = None
    is_active: bool
    email_verified: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class SocialAccountResponse(BaseModel):
    """Social account response model."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider: str
    provider_user_id: str
    scope_granted: Optional[List[str]] = None
    is_primary: bool
    connected_at: datetime
    last_used_at: Optional[datetime] = None


class TokenResponse(BaseModel):
    """JWT token response model."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    refresh_token: Optional[str] = Field(None, description="JWT refresh token")


class GoogleLoginResponse(BaseModel):
    """Google OAuth login response model."""

    auth_url: str = Field(..., description="Google OAuth authorization URL")
    state: str = Field(..., description="CSRF protection state parameter")


class LoginResponse(BaseModel):
    """Login response model."""

    user: UserResponse
    tokens: TokenResponse
    is_new_user: bool = Field(
        default=False, description="Whether this is a new user registration"
    )


class UserWithSocialAccountsResponse(BaseModel):
    """User with social accounts response model."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: str
    user_level: int
    profile_image_url: Optional[str] = None
    is_active: bool
    email_verified: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    social_accounts: List[SocialAccountResponse] = []


class MessageResponse(BaseModel):
    """Generic message response model."""

    message: str = Field(..., description="Response message")
