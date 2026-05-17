"""mobile gap fix: tasks fields, appointment consultation_type, documents fields, enrollments table

Revision ID: 0009_mobile_gap_fix
Revises: 0008_messages_images
Create Date: 2026-05-17 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009_mobile_gap_fix"
down_revision = "0008_messages_images"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- tasks: new fields ---
    op.add_column("tasks", sa.Column("task_type", sa.String(20), nullable=False, server_default="assignment"))
    op.add_column("tasks", sa.Column("time_from", sa.Time(), nullable=True))
    op.add_column("tasks", sa.Column("time_to", sa.Time(), nullable=True))
    op.add_column("tasks", sa.Column("location", sa.String(300), nullable=True))
    op.add_column("tasks", sa.Column("reminder_minutes", sa.SmallInteger(), nullable=True))

    # --- appointments: consultation_type ---
    op.add_column("appointments", sa.Column("consultation_type", sa.String(20), nullable=False, server_default="video"))

    # --- student_documents: category, status, expires_at ---
    op.add_column("student_documents", sa.Column("category", sa.String(20), nullable=False, server_default="other"))
    op.add_column("student_documents", sa.Column("status", sa.String(20), nullable=False, server_default="active"))
    op.add_column("student_documents", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))

    # --- enrollments table ---
    op.create_table(
        "enrollments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("university_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("universities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="selected"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_enrollments_student_uni", "enrollments", ["student_id", "university_id"], unique=True)


def downgrade() -> None:
    op.drop_index("idx_enrollments_student_uni", table_name="enrollments")
    op.drop_table("enrollments")

    op.drop_column("student_documents", "expires_at")
    op.drop_column("student_documents", "status")
    op.drop_column("student_documents", "category")

    op.drop_column("appointments", "consultation_type")

    op.drop_column("tasks", "reminder_minutes")
    op.drop_column("tasks", "location")
    op.drop_column("tasks", "time_to")
    op.drop_column("tasks", "time_from")
    op.drop_column("tasks", "task_type")
