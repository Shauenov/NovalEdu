"""news and calendar

Revision ID: 0003_news_calendar
Revises: 0002_universities
Create Date: 2026-05-01 00:20:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0003_news_calendar'
down_revision = '0002_universities'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'news',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('author_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('cover_url', sa.String(length=500), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('event_date', sa.Date(), nullable=True),
        sa.Column('external_url', sa.String(length=500), nullable=True),
        sa.Column('is_published', sa.Boolean(), nullable=True),
        sa.Column('views_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    )
    op.create_index('idx_news_category', 'news', ['category'])
    op.create_index('idx_news_published', 'news', ['is_published', 'created_at'])

    op.create_table(
        'calendar_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('event_type', sa.String(length=30), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('all_day', sa.Boolean(), nullable=True),
        sa.Column('color', sa.String(length=7), nullable=True),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('source_type', sa.String(length=30), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    )
    op.create_index('idx_calendar_user_time', 'calendar_events', ['user_id', 'start_time'])


def downgrade() -> None:
    op.drop_index('idx_calendar_user_time', table_name='calendar_events')
    op.drop_table('calendar_events')

    op.drop_index('idx_news_published', table_name='news')
    op.drop_index('idx_news_category', table_name='news')
    op.drop_table('news')
