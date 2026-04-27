"""mark giyeon journal as wuxia genre

Revision ID: 9f31b7c2a8d4
Revises: 72c1f5a14d56
Create Date: 2026-04-21 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9f31b7c2a8d4"
down_revision: Union[str, None] = "72c1f5a14d56"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        UPDATE scenarios
        SET genre = 'wuxia'
        WHERE name = '기연 일지'
          AND game_type = 'progression'
        """)


def downgrade() -> None:
    op.execute("""
        UPDATE scenarios
        SET genre = 'historical'
        WHERE name = '기연 일지'
          AND game_type = 'progression'
          AND genre = 'wuxia'
        """)
