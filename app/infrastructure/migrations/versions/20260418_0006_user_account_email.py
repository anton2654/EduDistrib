"""Add optional email column to user_accounts.

Revision ID: 20260418_0006
Revises: a031c6050a6e
Create Date: 2026-04-18 00:10:00
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260418_0006"
down_revision: str | None = "a031c6050a6e"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_accounts",
        sa.Column("email", sa.String(length=255), nullable=True),
    )
    op.create_unique_constraint(
        "uq_user_accounts_email",
        "user_accounts",
        ["email"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_user_accounts_email", "user_accounts", type_="unique")
    op.drop_column("user_accounts", "email")
