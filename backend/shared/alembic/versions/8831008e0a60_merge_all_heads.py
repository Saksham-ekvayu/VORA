"""Merge all heads - resolve multiple migration branches."""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "8831008e0a60"
down_revision = ("0d628a4de619", "aabd46f61d4a")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This is a merge migration - no operations needed
    pass


def downgrade() -> None:
    # This is a merge migration - no operations needed
    pass
