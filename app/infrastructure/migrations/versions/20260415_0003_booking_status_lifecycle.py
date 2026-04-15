"""Add booking status lifecycle and active-booking unique index.

Revision ID: 20260415_0003
Revises: 20260414_0002
Create Date: 2026-04-15 00:00:00
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "20260415_0003"
down_revision: str | None = "20260414_0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            CREATE TYPE booking_status AS ENUM ('active', 'cancelled', 'completed');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """,
    )

    booking_status_enum = postgresql.ENUM(
        "active",
        "cancelled",
        "completed",
        name="booking_status",
        create_type=False,
    )

    op.add_column(
        "bookings",
        sa.Column(
            "status",
            booking_status_enum,
            nullable=True,
            server_default=sa.text("'active'"),
        ),
    )

    op.execute("UPDATE bookings SET status = 'active' WHERE status IS NULL")

    op.alter_column("bookings", "status", nullable=False)

    op.drop_constraint("uq_bookings_student_slot", "bookings", type_="unique")

    op.create_index(
        "uq_bookings_active_student_slot",
        "bookings",
        ["student_id", "slot_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_index("ix_bookings_slot_status", "bookings", ["slot_id", "status"])
    op.create_index("ix_bookings_student_status", "bookings", ["student_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_bookings_student_status", table_name="bookings")
    op.drop_index("ix_bookings_slot_status", table_name="bookings")
    op.drop_index("uq_bookings_active_student_slot", table_name="bookings")

    op.create_unique_constraint(
        "uq_bookings_student_slot",
        "bookings",
        ["student_id", "slot_id"],
    )

    op.drop_column("bookings", "status")
    op.execute("DROP TYPE IF EXISTS booking_status")
