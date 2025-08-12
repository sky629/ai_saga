"""Add apple to oauth_provider enum

Revision ID: 3ec070505365
Revises: 001
Create Date: 2025-08-04 16:12:06.992233

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3ec070505365"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 'apple' to the oauth_provider enum
    op.execute("ALTER TYPE oauth_provider ADD VALUE 'apple'")


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values directly
    # This would require recreating the enum type, which is complex
    # For now, we'll leave the enum value in place
    pass
