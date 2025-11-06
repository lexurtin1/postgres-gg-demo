"""merge heads

Revision ID: 39e732adbb6c
Revises: 9b2b3d1a1cde, bb01a1add
Create Date: 2025-11-06 14:39:04.094060

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '39e732adbb6c'
down_revision: Union[str, Sequence[str], None] = ('9b2b3d1a1cde', 'bb01a1add')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
