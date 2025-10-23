"""Create User table

Revision ID: 494cf4353a8b
Revises: 
Create Date: 2025-10-23 14:58:14.852723

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
# Down revision will be None for the initial migration, purpose of variable is to point to the id of the previous revision in our alembic configuration
revision: str = '494cf4353a8b'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



# we can add code to define what happens in the migration 
def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('username', sa.String(length=50), nullable=False, unique=True),
        sa.Column('email', sa.String(length=120), nullable=False, unique=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('is_active', sa.Boolean, server_default=sa.sql.expression.true(), nullable=False)
     )
    
   

# we add code to tell alembic how to revers the migration
def downgrade() -> None:
    op.drop_table('users')
    op.drop_table('documents')
