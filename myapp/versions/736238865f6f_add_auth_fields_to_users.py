"""Add password_hash and email columns to users (idempotent)"""

from alembic import op
import sqlalchemy as sa

# Alembic identifiers
revision = '736238865f6f'
down_revision = '8174e2163cdb'
branch_labels = None
depends_on = None


def _column_names(bind, table: str) -> set[str]:
    inspector = sa.inspect(bind)
    return {c['name'] for c in inspector.get_columns(table)}


def upgrade():
    bind = op.get_bind()
    cols = _column_names(bind, 'users')

    # Add columns only if missing
    with op.batch_alter_table('users') as batch_op:
        if 'email' not in cols:
            batch_op.add_column(sa.Column('email', sa.String(length=255), nullable=True))
        if 'password_hash' not in cols:
            batch_op.add_column(sa.Column('password_hash', sa.String(length=255), nullable=True))
        if 'created_at' not in cols:
            batch_op.add_column(sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False))

    # Ensure unique constraint on email (Postgres-safe guard)
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE table_name = 'users' AND constraint_name = 'uq_users_email'
            ) THEN
                ALTER TABLE users ADD CONSTRAINT uq_users_email UNIQUE (email);
            END IF;
        END$$;
        """
    )


def downgrade():
    # Drop unique constraint if present
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE table_name = 'users' AND constraint_name = 'uq_users_email'
            ) THEN
                ALTER TABLE users DROP CONSTRAINT uq_users_email;
            END IF;
        END$$;
        """
    )

    # Drop columns if present
    bind = op.get_bind()
    cols = _column_names(bind, 'users')
    with op.batch_alter_table('users') as batch_op:
        if 'created_at' in cols:
            batch_op.drop_column('created_at')
        if 'password_hash' in cols:
            batch_op.drop_column('password_hash')
        if 'email' in cols:
            batch_op.drop_column('email')
