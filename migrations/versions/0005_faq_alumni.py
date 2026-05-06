"""faq and alumni

Revision ID: 0005_faq_alumni
Revises: 0004_roadmaps
Create Date: 2026-05-01 00:40:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0005_faq_alumni'
down_revision = '0004_roadmaps'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'faqs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('order_index', sa.SmallInteger(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    )

    op.create_table(
        'alumni_stories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('author_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('student_name', sa.String(length=255), nullable=False),
        sa.Column('graduation_year', sa.SmallInteger(), nullable=True),
        sa.Column('university_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('universities.id'), nullable=True),
        sa.Column('university_name', sa.String(length=300), nullable=True),
        sa.Column('program_name', sa.String(length=300), nullable=True),
        sa.Column('scholarship_type', sa.String(length=200), nullable=True),
        sa.Column('story_text', sa.Text(), nullable=False),
        sa.Column('photo_url', sa.String(length=500), nullable=True),
        sa.Column('gpa_at_time', sa.Numeric(3, 2), nullable=True),
        sa.Column('ielts_at_time', sa.Numeric(3, 1), nullable=True),
        sa.Column('sat_at_time', sa.SmallInteger(), nullable=True),
        sa.Column('is_published', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('alumni_stories')
    op.drop_table('faqs')
