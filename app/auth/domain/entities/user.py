"""User Entity."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.auth.domain.value_objects import UserLevel


class UserEntity(BaseModel):
    """사용자 도메인 엔티티."""

    model_config = {"frozen": True}

    id: UUID
    email: str
    name: str
    profile_image_url: Optional[str] = None
    user_level: UserLevel = UserLevel.NORMAL
    is_active: bool = True
    email_verified: bool = False
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None
