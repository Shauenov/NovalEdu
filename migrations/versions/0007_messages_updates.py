"""messages updates

Revision ID: 0007_messages_updates
Revises: 0006_appointments_updates
Create Date: 2026-05-02 13:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0007_messages_updates"
down_revision = "0006_appointments_updates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "messages",
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("messages", "read_at")
    op.drop_column("conversations", "last_message_at")
