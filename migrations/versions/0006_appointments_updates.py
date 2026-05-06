"""appointments updates

Revision ID: 0006_appointments_updates
Revises: 0005_faq_alumni
Create Date: 2026-05-02 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0006_appointments_updates"
down_revision = "0005_faq_alumni"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "availability_slots",
        sa.Column("duration_min", sa.SmallInteger(), server_default=sa.text("45"), nullable=False),
    )
    op.add_column(
        "appointments",
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "appointments",
        sa.Column("cancel_reason", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("appointments", "cancel_reason")
    op.drop_column("appointments", "cancelled_at")
    op.drop_column("availability_slots", "duration_min")
