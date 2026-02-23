"""add embedding to game_messages

Revision ID: d2b3c4d5e6f7
Revises: c1a2b3d4e5f6
Create Date: 2026-02-23 14:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "d2b3c4d5e6f7"
down_revision: Union[str, None] = "c1a2b3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # pgvector 확장이 설치되어 있지 않을 수 있으므로 추가
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.add_column(
        "game_messages",
        sa.Column("embedding", Vector(768), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("game_messages", "embedding")
