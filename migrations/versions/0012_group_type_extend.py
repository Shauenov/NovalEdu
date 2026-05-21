"""extend group_type column to support subgroups D1, D2, F1-F4

Revision ID: 0012_group_type_extend
Revises: 0011_task_history
Create Date: 2026-05-20 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0012_group_type_extend"
down_revision = "0011_task_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Increase column length from 1 to 2 to accommodate D1, D2, F1, F2, F3, F4
    op.alter_column(
        "student_profiles",
        "group_type",
        existing_type=sa.String(1),
        type_=sa.String(2),
        existing_nullable=False,
    )


def downgrade() -> None:
    # Truncate any subgroup values back to the parent letter before shrinking
    op.execute(
        "UPDATE student_profiles SET group_type = LEFT(group_type, 1)"
    )
    op.alter_column(
        "student_profiles",
        "group_type",
        existing_type=sa.String(2),
        type_=sa.String(1),
        existing_nullable=False,
    )
