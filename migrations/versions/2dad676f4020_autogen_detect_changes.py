"""autogen: detect changes

Revision ID: 2dad676f4020
Revises: 0010_profile_settings_sessions
Create Date: 2026-05-17 17:26:18.674403
"""

# revision identifiers, used by Alembic.
revision = '2dad676f4020'
down_revision = '0010_profile_settings_sessions'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

from sqlalchemy.dialects import postgresql


def upgrade():
    pass


def downgrade():
    pass
