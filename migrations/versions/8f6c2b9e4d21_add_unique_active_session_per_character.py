"""add unique active session constraint per character

Revision ID: 8f6c2b9e4d21
Revises: 72c1f5a14d56
Create Date: 2026-03-04 12:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "8f6c2b9e4d21"
down_revision: Union[str, None] = "72c1f5a14d56"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "uq_game_sessions_character_active",
        "game_sessions",
        ["character_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_game_sessions_character_active", table_name="game_sessions"
    )
