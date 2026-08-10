"""Merge multiple heads

Revision ID: 0d628a4de619
Revises: 8ae65b5a8195, 0001_add_tables
Create Date: 2026-08-10 11:28:33.266185

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0d628a4de619"
down_revision: Union[str, Sequence[str], None] = ("8ae65b5a8195", "0001_add_tables")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
