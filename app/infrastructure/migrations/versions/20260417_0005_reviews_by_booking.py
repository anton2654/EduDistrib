"""Tie reviews to concrete booking.

Revision ID: 20260417_0005
Revises: 20260417_0004
Create Date: 2026-04-17 01:00:00
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260417_0005"
down_revision: str | None = "20260417_0004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("reviews", sa.Column("booking_id", sa.Integer(), nullable=True))

    op.execute(
        sa.text(
            """
                        UPDATE reviews
                        SET booking_id = (
                                SELECT b.id
                                FROM bookings AS b
                                JOIN teacher_slots AS ts ON ts.id = b.slot_id
                                WHERE b.student_id = reviews.student_id
                                    AND ts.teacher_id = reviews.teacher_id
                                    AND b.status = 'completed'
                                ORDER BY ts.ends_at DESC, b.id DESC
                                LIMIT 1
                        )
                        WHERE reviews.booking_id IS NULL
            """,
        ),
    )

    op.execute(sa.text("DELETE FROM reviews WHERE booking_id IS NULL"))

    op.drop_constraint("uq_reviews_teacher_student", "reviews", type_="unique")

    op.alter_column("reviews", "booking_id", nullable=False)
    op.create_foreign_key(
        "fk_reviews_booking_id_bookings",
        "reviews",
        "bookings",
        ["booking_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint("uq_reviews_booking", "reviews", ["booking_id"])
    op.create_index("ix_reviews_booking_id", "reviews", ["booking_id"])


def downgrade() -> None:
    op.drop_index("ix_reviews_booking_id", table_name="reviews")
    op.drop_constraint("uq_reviews_booking", "reviews", type_="unique")
    op.drop_constraint("fk_reviews_booking_id_bookings", "reviews", type_="foreignkey")

    op.alter_column("reviews", "booking_id", nullable=True)
    op.create_unique_constraint(
        "uq_reviews_teacher_student",
        "reviews",
        ["teacher_id", "student_id"],
    )
    op.drop_column("reviews", "booking_id")
