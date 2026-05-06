"""roadmaps

Revision ID: 0004_roadmaps
Revises: 0003_news_calendar
Create Date: 2026-05-01 00:30:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0004_roadmaps'
down_revision = '0003_news_calendar'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'roadmaps',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('target_type', sa.String(length=50), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    )

    op.create_table(
        'roadmap_template_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('roadmap_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('roadmaps.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('order_index', sa.SmallInteger(), nullable=False),
        sa.Column('days_offset', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    )
    op.create_index('idx_roadmap_tasks_roadmap', 'roadmap_template_tasks', ['roadmap_id'])

    op.create_table(
        'student_roadmaps',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('roadmap_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('roadmaps.id', ondelete='SET NULL'), nullable=True),
        sa.Column('assigned_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('student_roadmaps')
    op.drop_index('idx_roadmap_tasks_roadmap', table_name='roadmap_template_tasks')
    op.drop_table('roadmap_template_tasks')
    op.drop_table('roadmaps')
