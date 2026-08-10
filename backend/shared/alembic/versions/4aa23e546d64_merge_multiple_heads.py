"""merge multiple heads

Revision ID: 4aa23e546d64
Revises: 0d628a4de619, 4feeeb66a776
Create Date: 2026-08-10 14:21:37.534172

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4aa23e546d64"
down_revision: Union[str, Sequence[str], None] = ("0d628a4de619", "4feeeb66a776")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
