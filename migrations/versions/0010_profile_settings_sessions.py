"""profile personal fields, notification settings table, session metadata

Revision ID: 0010_profile_settings_sessions
Revises: 0009_mobile_gap_fix
Create Date: 2026-05-17 14:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0010_profile_settings_sessions"
down_revision = "0009_mobile_gap_fix"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- student_profiles: personal info fields ---
    op.add_column("student_profiles", sa.Column("phone", sa.String(30), nullable=True))
    op.add_column("student_profiles", sa.Column("gender", sa.String(10), nullable=True))
    op.add_column("student_profiles", sa.Column("birth_date", sa.Date(), nullable=True))
    op.add_column("student_profiles", sa.Column("school_name", sa.String(300), nullable=True))

    # --- student_profiles: application settings fields ---
    op.add_column("student_profiles", sa.Column("degree_level", sa.String(20), nullable=True))
    op.add_column("student_profiles", sa.Column("target_countries", sa.Text(), nullable=True))
    op.add_column("student_profiles", sa.Column("budget_max", sa.Integer(), nullable=True))

    # --- refresh_tokens: session metadata ---
    op.add_column("refresh_tokens", sa.Column("device_name", sa.String(200), nullable=True))
    op.add_column("refresh_tokens", sa.Column("ip_address", sa.String(50), nullable=True))
    op.add_column(
        "refresh_tokens",
        sa.Column("last_used_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- user_notification_settings table ---
    op.create_table(
        "user_notification_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("push_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("email_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("deadline_alerts", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("roadmap_changes", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("new_messages", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("task_updates", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("security_alerts", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("app_updates", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("user_notification_settings")

    op.drop_column("refresh_tokens", "last_used_at")
    op.drop_column("refresh_tokens", "ip_address")
    op.drop_column("refresh_tokens", "device_name")

    op.drop_column("student_profiles", "budget_max")
    op.drop_column("student_profiles", "target_countries")
    op.drop_column("student_profiles", "degree_level")
    op.drop_column("student_profiles", "school_name")
    op.drop_column("student_profiles", "birth_date")
    op.drop_column("student_profiles", "gender")
    op.drop_column("student_profiles", "phone")
