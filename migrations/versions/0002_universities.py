"""universities

Revision ID: 0002_universities
Revises: 0001_initial
Create Date: 2026-05-01 00:10:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0002_universities'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'universities',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(length=300), nullable=False),
        sa.Column('country', sa.String(length=100), nullable=False),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('logo_url', sa.String(length=500), nullable=True),
        sa.Column('cover_image_url', sa.String(length=500), nullable=True),
        sa.Column('website_url', sa.String(length=500), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('acceptance_rate', sa.Numeric(5, 2), nullable=True),
        sa.Column('total_students', sa.Integer(), nullable=True),
        sa.Column('international_pct', sa.Numeric(5, 2), nullable=True),
        sa.Column('qs_ranking', sa.SmallInteger(), nullable=True),
        sa.Column('the_ranking', sa.SmallInteger(), nullable=True),
        sa.Column('language_of_instr', sa.String(length=100), nullable=True),
        sa.Column('is_published', sa.Boolean(), nullable=True),
        sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    )
    op.create_index('idx_universities_country', 'universities', ['country'])
    op.create_index('idx_universities_published', 'universities', ['is_published'])

    op.create_table(
        'university_programs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('university_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('universities.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=300), nullable=False),
        sa.Column('degree_level', sa.String(length=50), nullable=True),
        sa.Column('field', sa.String(length=100), nullable=True),
        sa.Column('min_gpa', sa.Numeric(3, 2), nullable=True),
        sa.Column('min_ielts', sa.Numeric(3, 1), nullable=True),
        sa.Column('min_sat', sa.SmallInteger(), nullable=True),
        sa.Column('tuition_usd', sa.Integer(), nullable=True),
        sa.Column('scholarship_info', sa.Text(), nullable=True),
        sa.Column('application_fee', sa.Integer(), nullable=True),
        sa.Column('intake_seasons', sa.String(length=100), nullable=True),
        sa.Column('deadline', sa.Date(), nullable=True),
        sa.Column('campus_life', sa.Text(), nullable=True),
        sa.Column('requirements_text', sa.Text(), nullable=True),
        sa.Column('apply_url', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    )
    op.create_index('idx_programs_university', 'university_programs', ['university_id'])
    op.create_index('idx_programs_field', 'university_programs', ['field'])


def downgrade() -> None:
    op.drop_index('idx_programs_field', table_name='university_programs')
    op.drop_index('idx_programs_university', table_name='university_programs')
    op.drop_table('university_programs')

    op.drop_index('idx_universities_published', table_name='universities')
    op.drop_index('idx_universities_country', table_name='universities')
    op.drop_table('universities')
