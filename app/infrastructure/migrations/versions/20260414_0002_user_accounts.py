"""Add user accounts for role-based authentication.

Revision ID: 20260414_0002
Revises: 20260414_0001
Create Date: 2026-04-14 01:00:00
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260414_0002"
down_revision: str | None = "20260414_0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            CREATE TYPE user_role AS ENUM ('student', 'teacher', 'admin');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """,
    )

    user_role_enum = postgresql.ENUM(
        "student",
        "teacher",
        "admin",
        name="user_role",
        create_type=False,
    )

    op.create_table(
        "user_accounts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", user_role_enum, nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=True),
        sa.Column("teacher_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["teacher_id"], ["teachers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
        sa.UniqueConstraint("student_id"),
        sa.UniqueConstraint("teacher_id"),
    )


def downgrade() -> None:
    op.drop_table("user_accounts")
    op.execute("DROP TYPE IF EXISTS user_role")
