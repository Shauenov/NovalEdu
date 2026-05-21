"""news: add allow_calendar column

Revision ID: 0014_news_allow_calendar
Revises: 0013_rename_conductor_to_adviser
Create Date: 2026-05-21
"""

from alembic import op
import sqlalchemy as sa

revision = '0014_news_allow_calendar'
down_revision = '0013_rename_conductor_to_adviser'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'news',
        sa.Column('allow_calendar', sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column('news', 'allow_calendar')
