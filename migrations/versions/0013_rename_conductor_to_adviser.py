"""rename conductor to adviser

Revision ID: 0013_rename_conductor_to_adviser
Revises: 0012_group_type_extend
Create Date: 2026-05-21

"""
from alembic import op
import sqlalchemy as sa

revision = '0013_rename_conductor_to_adviser'
down_revision = '0012_group_type_extend'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Update role values in users table
    op.execute("UPDATE users SET role = 'adviser' WHERE role = 'conductor'")

    # Rename conductor_id -> adviser_id in availability_slots
    with op.batch_alter_table('availability_slots') as batch_op:
        batch_op.alter_column('conductor_id', new_column_name='adviser_id')

    # Drop old index, rename conductor_id -> adviser_id in appointments
    op.drop_index('idx_slots_conductor_time', table_name='availability_slots')
    op.create_index('idx_slots_adviser_time', 'availability_slots', ['adviser_id', 'start_time'])

    with op.batch_alter_table('appointments') as batch_op:
        batch_op.alter_column('conductor_id', new_column_name='adviser_id')

    # Rename conductor_id -> adviser_id in conversations
    op.drop_index('idx_conversation_users', table_name='conversations')
    with op.batch_alter_table('conversations') as batch_op:
        batch_op.alter_column('conductor_id', new_column_name='adviser_id')
    op.create_index('idx_conversation_users', 'conversations', ['student_id', 'adviser_id'], unique=True)


def downgrade() -> None:
    op.execute("UPDATE users SET role = 'conductor' WHERE role = 'adviser'")

    with op.batch_alter_table('availability_slots') as batch_op:
        batch_op.alter_column('adviser_id', new_column_name='conductor_id')

    op.drop_index('idx_slots_adviser_time', table_name='availability_slots')
    op.create_index('idx_slots_conductor_time', 'availability_slots', ['conductor_id', 'start_time'])

    with op.batch_alter_table('appointments') as batch_op:
        batch_op.alter_column('adviser_id', new_column_name='conductor_id')

    op.drop_index('idx_conversation_users', table_name='conversations')
    with op.batch_alter_table('conversations') as batch_op:
        batch_op.alter_column('adviser_id', new_column_name='conductor_id')
    op.create_index('idx_conversation_users', 'conversations', ['student_id', 'conductor_id'], unique=True)
