"""Add user type column

Revision ID: 8174e2163cdb
Revises: 494cf4353a8b
Create Date: 2025-10-23 15:53:48.069659

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8174e2163cdb'
down_revision: Union[str, Sequence[str], None] = '494cf4353a8b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users', 
        sa.Column('user_type', sa.String(length=20), nullable=False, server_default='regular')
        )


def downgrade() -> None:
    op.drop_column('users', 'user_type')
