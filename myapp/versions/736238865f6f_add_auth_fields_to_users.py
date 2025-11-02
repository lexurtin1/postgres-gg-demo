"""Add password_hash and email columns to users"""

from alembic import op
import sqlalchemy as sa

# Alembic identifiers
revision = '736238865f6f'    
down_revision = '8174e2163cdb'         
branch_labels = None
depends_on = None

def upgrade():
    # Alter the 'users' table to extend its layout
    with op.batch_alter_table('users') as batch_op:
        # Add an email column so each user has a unique address
        batch_op.add_column(sa.Column('email', sa.String(length=255), nullable=True))

        # Add a password_hash column to store the hashed password
        batch_op.add_column(sa.Column('password_hash', sa.String(length=255), nullable=True))

        # Add a timestamp so we know when the account was created
        batch_op.add_column(sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False))

        # Ensure emails are unique across users
        batch_op.create_unique_constraint('uq_users_email', ['email'])

def downgrade():
    # Revert the above changes on downgrade
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_constraint('uq_users_email', type_='unique')
        batch_op.drop_column('created_at')
        batch_op.drop_column('password_hash')
        batch_op.drop_column('email')
