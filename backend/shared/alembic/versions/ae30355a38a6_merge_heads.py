"""Merge heads

Revision ID: ae30355a38a6
Revises: 79b2c5571e8f, 837f3e37f9ec
Create Date: 2026-08-10 17:27:42.664595

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ae30355a38a6'
down_revision: Union[str, Sequence[str], None] = ('79b2c5571e8f', '837f3e37f9ec')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
