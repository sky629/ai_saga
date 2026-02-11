"""Game database models - Character, GameSession, Scenario.

All models use UUID v7 for IDs (time-sortable).
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from uuid_utils import uuid7

from app.common.storage.postgres import Base
from app.game.domain.value_objects import ScenarioDifficulty, ScenarioGenre


class Scenario(Base):
    """Game scenario/world template."""

    __tablename__ = "scenarios"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid7
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    world_setting: Mapped[str] = mapped_column(Text, nullable=False)
    initial_location: Mapped[str] = mapped_column(String(200), nullable=False)
    genre: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ScenarioGenre.FANTASY.value,
        index=True,
    )
    difficulty: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ScenarioDifficulty.NORMAL.value,
        index=True,
    )
    system_prompt_override: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    max_turns: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
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
    game_sessions: Mapped[list["GameSession"]] = relationship(
        "GameSession", back_populates="scenario"
    )

    def __repr__(self):
        return f"<Scenario(id={self.id}, name={self.name})>"


class Character(Base):
    """Player character in the game."""

    __tablename__ = "characters"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid7
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    scenario_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scenarios.id"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Character stats stored as JSON for flexibility
    stats: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=lambda: {"hp": 100, "max_hp": 100, "level": 1},
    )
    inventory: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=lambda: []
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
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
    game_sessions: Mapped[list["GameSession"]] = relationship(
        "GameSession", back_populates="character"
    )
    scenario: Mapped["Scenario"] = relationship("Scenario")

    def __repr__(self):
        return f"<Character(id={self.id}, name={self.name})>"


class GameSession(Base):
    """Active game session linking character to scenario."""

    __tablename__ = "game_sessions"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid7
    )
    character_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("characters.id"),
        nullable=False,
        index=True,
    )
    scenario_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scenarios.id"),
        nullable=False,
        index=True,
    )

    current_location: Mapped[str] = mapped_column(String(200), nullable=False)
    game_state: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=lambda: {}
    )

    # Session status: active, paused, completed, ended
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active", index=True
    )
    turn_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_turns: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    ending_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # victory, defeat, neutral

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    character: Mapped["Character"] = relationship(
        "Character", back_populates="game_sessions"
    )
    scenario: Mapped["Scenario"] = relationship(
        "Scenario", back_populates="game_sessions"
    )
    messages: Mapped[list["GameMessage"]] = relationship(
        "GameMessage",
        back_populates="session",
        order_by="GameMessage.created_at",
    )

    def __repr__(self):
        return f"<GameSession(id={self.id}, status={self.status})>"


class GameMessage(Base):
    """Message in a game session (player action or AI response).

    Includes embedding vector for RAG-based context retrieval.
    """

    __tablename__ = "game_messages"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid7
    )
    session_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("game_sessions.id"),
        nullable=False,
        index=True,
    )

    # Message type: user (player action) or assistant (AI response)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Parsed response data (for AI responses)
    parsed_response: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True
    )

    # Token usage for this message
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    image_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )  # 삽화 URL

    # Relationships
    session: Mapped["GameSession"] = relationship(
        "GameSession", back_populates="messages"
    )

    def __repr__(self):
        return f"<GameMessage(id={self.id}, role={self.role})>"
