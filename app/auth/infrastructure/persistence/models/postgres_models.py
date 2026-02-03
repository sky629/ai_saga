"""SQLAlchemy models for authentication system."""

import uuid
from datetime import datetime
from typing import List, Optional
from uuid_utils import uuid7

from pydantic import ConfigDict
from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.common.storage.postgres import Base


class User(Base):
    """User model."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    user_level: Mapped[int] = mapped_column(
        Integer, nullable=False, default=100
    )  # 100: normal, 1000: admin
    profile_image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    social_accounts: Mapped[List["SocialAccount"]] = relationship(
        "SocialAccount", back_populates="user", cascade="all, delete-orphan"
    )

    model_config = ConfigDict(from_attributes=True)

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"


# Create ENUM type for OAuth providers
oauth_provider_enum = ENUM("google", "apple", name="oauth_provider", create_type=True)


class SocialAccount(Base):
    """Social account model for OAuth connections."""

    __tablename__ = "social_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(oauth_provider_enum, nullable=False)
    provider_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_data: Mapped[dict] = mapped_column(JSONB, nullable=True)
    scope_granted: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String), nullable=True
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    connected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="social_accounts")

    def __repr__(self):
        return f"<SocialAccount(id={self.id}, provider={self.provider}, user_id={self.user_id})>"

    class Config:
        """Pydantic config."""

        from_attributes = True
