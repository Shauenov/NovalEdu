"""messages images support

Revision ID: 0008_messages_images
Revises: 0007_messages_updates
Create Date: 2026-05-15 09:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0008_messages_images"
down_revision = "0007_messages_updates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column("image_object_key", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "messages",
        sa.Column("image_content_type", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "messages",
        sa.Column("image_size", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("messages", "image_size")
    op.drop_column("messages", "image_content_type")
    op.drop_column("messages", "image_object_key")
