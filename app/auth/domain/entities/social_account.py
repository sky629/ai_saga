"""Social Account Entity."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel
from app.auth.domain.value_objects import AuthProvider

class SocialAccountEntity(BaseModel):
    """소셜 계정 도메인 엔티티."""
    model_config = {"frozen": True}

    id: UUID
    user_id: UUID
    provider: AuthProvider
    provider_user_id: str
    provider_data: dict
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    last_used_at: datetime
