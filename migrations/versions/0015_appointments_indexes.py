"""appointments: add indexes for adviser/student/slot lookups

Revision ID: 0015_appointments_indexes
Revises: 0014_news_allow_calendar
Create Date: 2026-05-21
"""

from alembic import op

revision = '0015_appointments_indexes'
down_revision = '0014_news_allow_calendar'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index('idx_appt_adviser_created', 'appointments', ['adviser_id', 'created_at'])
    op.create_index('idx_appt_student_created', 'appointments', ['student_id', 'created_at'])
    op.create_index('idx_appt_slot', 'appointments', ['slot_id'])


def downgrade() -> None:
    op.drop_index('idx_appt_slot', table_name='appointments')
    op.drop_index('idx_appt_student_created', table_name='appointments')
    op.drop_index('idx_appt_adviser_created', table_name='appointments')
