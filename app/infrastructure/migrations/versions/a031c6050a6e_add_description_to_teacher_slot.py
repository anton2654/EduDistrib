"""add description to teacher_slot

Revision ID: a031c6050a6e
Revises: 20260417_0005
Create Date: 2026-04-17 18:39:47.678121

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision: str = 'a031c6050a6e'
down_revision: Union[str, None] = '20260417_0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('teacher_slots', sa.Column('description', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('teacher_slots', 'description')
