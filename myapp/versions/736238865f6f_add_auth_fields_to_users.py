"""Add password_hash and email columns to users"""

from alembic import op
import sqlalchemy as sa

# Alembic identifiers
revision = '736238865f6f'    
down_revision = '8174e2163cdb'         
branch_labels = None
depends_on = None

def upgrade():
    # I enter the 'users' table to extend its layout
    with op.batch_alter_table('users') as batch_op:
        # I add an email column so each staff member has a unique address
        batch_op.add_column(sa.Column('email', sa.String(length=255), nullable=True))

        # I add a password_hash column to store the scrambled version of their badge code (password)
        batch_op.add_column(sa.Column('password_hash', sa.String(length=255), nullable=True))

        # I add a timestamp so we know when the badge was issued
        batch_op.add_column(sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False))

        # I make sure no two staff share the same email address
        batch_op.create_unique_constraint('uq_users_email', ['email'])

def downgrade():
    # I undo the above if we ever roll back this construction
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_constraint('uq_users_email', type_='unique')
        batch_op.drop_column('created_at')
        batch_op.drop_column('password_hash')
        batch_op.drop_column('email')
