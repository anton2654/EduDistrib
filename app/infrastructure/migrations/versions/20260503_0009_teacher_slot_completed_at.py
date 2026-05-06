"""Add completed marker to teacher slots.

Revision ID: 20260503_0009
Revises: 20260503_0008
Create Date: 2026-05-03 13:55:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260503_0009"
down_revision: str | None = "20260503_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("teacher_slots", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("teacher_slots", "completed_at")
