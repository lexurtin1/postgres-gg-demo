"""Add password_hash to users (idempotent)

I add a nullable varchar(255) column named password_hash to the users table.
I use a raw ALTER TABLE ... IF NOT EXISTS so it succeeds even if another
earlier migration already added the column on some databases.
"""

from alembic import op  # I use Alembic's operations handle
import sqlalchemy as sa  # I keep this for completeness (not strictly required)

# Alembic identifiers — set down_revision to the current head in this project
revision = 'a12b34c56d78'
down_revision = '9b1a2c3d4e5f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # I run an idempotent ALTER so applying twice is safe on Postgres.
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255)")


def downgrade() -> None:
    # I remove the column on downgrade; IF EXISTS keeps it safe if already gone.
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS password_hash")

