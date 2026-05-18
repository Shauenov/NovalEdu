"""add task_history table

Revision ID: 0011_task_history
Revises: 0010_profile_settings_sessions
Create Date: 2026-05-17 20:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0011_task_history"
down_revision = "0010_profile_settings_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "task_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "changed_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("old_value", sa.String(300), nullable=True),
        sa.Column("new_value", sa.String(300), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("idx_task_history_task_id", "task_history", ["task_id"])


def downgrade() -> None:
    op.drop_index("idx_task_history_task_id", table_name="task_history")
    op.drop_table("task_history")
