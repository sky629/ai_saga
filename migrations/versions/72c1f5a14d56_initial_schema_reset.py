"""initial schema reset

Revision ID: 72c1f5a14d56
Revises:
Create Date: 2026-03-03 16:45:44.335676

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import VECTOR
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "72c1f5a14d56"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "scenarios",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("world_setting", sa.Text(), nullable=False),
        sa.Column("initial_location", sa.String(length=200), nullable=False),
        sa.Column("genre", sa.String(length=50), nullable=False),
        sa.Column("difficulty", sa.String(length=20), nullable=False),
        sa.Column("system_prompt_override", sa.Text(), nullable=True),
        sa.Column("max_turns", sa.Integer(), nullable=False),
        sa.Column(
            "tags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("thumbnail_url", sa.String(length=500), nullable=True),
        sa.Column("hook", sa.Text(), nullable=True),
        sa.Column("recommended_for", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_scenarios_difficulty"),
        "scenarios",
        ["difficulty"],
        unique=False,
    )
    op.create_index(
        op.f("ix_scenarios_genre"), "scenarios", ["genre"], unique=False
    )
    op.create_index(
        op.f("ix_scenarios_name"), "scenarios", ["name"], unique=False
    )

    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("user_level", sa.Integer(), nullable=False),
        sa.Column("game_level", sa.Integer(), nullable=False),
        sa.Column("game_experience", sa.Integer(), nullable=False),
        sa.Column("game_current_experience", sa.Integer(), nullable=False),
        sa.Column("profile_image_url", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("email_verified", sa.Boolean(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "characters",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("scenario_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "profile",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "stats", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "inventory",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenarios.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_characters_scenario_id"),
        "characters",
        ["scenario_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_characters_user_id"), "characters", ["user_id"], unique=False
    )

    op.create_table(
        "social_accounts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "provider",
            postgresql.ENUM("google", "apple", name="oauth_provider"),
            nullable=False,
        ),
        sa.Column("provider_user_id", sa.String(length=255), nullable=False),
        sa.Column(
            "provider_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("scope_granted", sa.ARRAY(sa.String()), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column(
            "connected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider",
            "provider_user_id",
            name="uq_social_accounts_provider_user",
        ),
    )
    op.create_index(
        op.f("ix_social_accounts_user_id"),
        "social_accounts",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "game_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("character_id", sa.UUID(), nullable=False),
        sa.Column("scenario_id", sa.UUID(), nullable=False),
        sa.Column("current_location", sa.String(length=200), nullable=False),
        sa.Column(
            "game_state",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("turn_count", sa.Integer(), nullable=False),
        sa.Column("max_turns", sa.Integer(), nullable=False),
        sa.Column("ending_type", sa.String(length=50), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "last_activity_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"]),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenarios.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_game_sessions_character_id"),
        "game_sessions",
        ["character_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_game_sessions_scenario_id"),
        "game_sessions",
        ["scenario_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_game_sessions_status"),
        "game_sessions",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_game_sessions_user_id"),
        "game_sessions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "uq_game_sessions_character_active",
        "game_sessions",
        ["character_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "game_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "parsed_response",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["game_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_game_messages_session_id"),
        "game_messages",
        ["session_id"],
        unique=False,
    )
    op.create_table(
        "game_memory_documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("source_message_id", sa.UUID(), nullable=True),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("memory_type", sa.String(length=50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "parsed_response",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("embedding", VECTOR(dim=768), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["session_id"], ["game_sessions.id"]),
        sa.ForeignKeyConstraint(["source_message_id"], ["game_messages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_game_memory_documents_session_id"),
        "game_memory_documents",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_game_memory_documents_source_message_id"),
        "game_memory_documents",
        ["source_message_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_game_memory_documents_source_message_id"),
        table_name="game_memory_documents",
    )
    op.drop_index(
        op.f("ix_game_memory_documents_session_id"),
        table_name="game_memory_documents",
    )
    op.drop_table("game_memory_documents")

    op.drop_index(
        op.f("ix_game_messages_session_id"), table_name="game_messages"
    )
    op.drop_table("game_messages")

    op.drop_index(
        "uq_game_sessions_character_active", table_name="game_sessions"
    )
    op.drop_index(op.f("ix_game_sessions_user_id"), table_name="game_sessions")
    op.drop_index(op.f("ix_game_sessions_status"), table_name="game_sessions")
    op.drop_index(
        op.f("ix_game_sessions_scenario_id"), table_name="game_sessions"
    )
    op.drop_index(
        op.f("ix_game_sessions_character_id"), table_name="game_sessions"
    )
    op.drop_table("game_sessions")

    op.drop_index(
        op.f("ix_social_accounts_user_id"), table_name="social_accounts"
    )
    op.drop_table("social_accounts")
    op.execute("DROP TYPE oauth_provider")

    op.drop_index(op.f("ix_characters_user_id"), table_name="characters")
    op.drop_index(op.f("ix_characters_scenario_id"), table_name="characters")
    op.drop_table("characters")

    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

    op.drop_index(op.f("ix_scenarios_name"), table_name="scenarios")
    op.drop_index(op.f("ix_scenarios_genre"), table_name="scenarios")
    op.drop_index(op.f("ix_scenarios_difficulty"), table_name="scenarios")
    op.drop_table("scenarios")
