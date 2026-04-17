"""Add reviews table for teacher ratings.

Revision ID: 20260417_0004
Revises: 20260415_0003
Create Date: 2026-04-17 00:00:00
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260417_0004"
down_revision: str | None = "20260415_0003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("teacher_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.String(length=1000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("rating >= 1 AND rating <= 5", name="ck_reviews_rating_range"),
        sa.ForeignKeyConstraint(["teacher_id"], ["teachers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("teacher_id", "student_id", name="uq_reviews_teacher_student"),
    )

    op.create_index("ix_reviews_teacher_id", "reviews", ["teacher_id"])
    op.create_index("ix_reviews_student_id", "reviews", ["student_id"])


def downgrade() -> None:
    op.drop_index("ix_reviews_student_id", table_name="reviews")
    op.drop_index("ix_reviews_teacher_id", table_name="reviews")
    op.drop_table("reviews")
