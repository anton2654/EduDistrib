"""Add address to teacher slots.

Revision ID: 20260503_0008
Revises: 20260420_0007
Create Date: 2026-05-03 13:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260503_0008"
down_revision: str | None = "20260420_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("teacher_slots", sa.Column("address", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("teacher_slots", "address")
