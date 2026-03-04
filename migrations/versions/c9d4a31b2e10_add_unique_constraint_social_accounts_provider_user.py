"""add unique constraint for social account provider identity

Revision ID: c9d4a31b2e10
Revises: 8f6c2b9e4d21
Create Date: 2026-03-04 16:40:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9d4a31b2e10"
down_revision: Union[str, None] = "8f6c2b9e4d21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_social_accounts_provider_user",
        "social_accounts",
        ["provider", "provider_user_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_social_accounts_provider_user",
        "social_accounts",
        type_="unique",
    )
