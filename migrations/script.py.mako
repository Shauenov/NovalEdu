
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision if down_revision else None}
Create Date: ${create_date}
"""

# revision identifiers, used by Alembic.
revision = '${up_revision}'
down_revision = ${repr(down_revision) if down_revision else None}
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

${imports if imports else ""}


def upgrade():
% if upgrade_ops:
% for stmt in upgrade_ops:
    ${stmt}
% endfor
% else:
    pass
% endif


def downgrade():
% if downgrade_ops:
% for stmt in downgrade_ops:
    ${stmt}
% endfor
% else:
    pass
% endif
