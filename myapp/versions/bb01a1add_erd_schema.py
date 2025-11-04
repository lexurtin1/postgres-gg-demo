"""Add ERD entities and link to existing tables

Revision ID: bb01a1add
Revises: 9b1a2c3d4e5f
Create Date: 2025-11-04 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "bb01a1add"
# Chain after a12b34c56d78 to avoid multiple heads
down_revision: Union[str, Sequence[str], None] = "a12b34c56d78"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(bind, table: str) -> set[str]:
    inspector = sa.inspect(bind)
    return {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    # Organisations
    op.create_table(
        "organisations",
        sa.Column("id", sa.String(length=36), primary_key=True),  # UUID as string
        sa.Column("legal_name", sa.String(length=255), nullable=False),
        sa.Column("reg_number", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    # Banks
    op.create_table(
        "banks",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("bic", sa.String(length=20), nullable=True),
        sa.Column("country", sa.String(length=2), nullable=True),
    )

    # Vendor checks
    op.create_table(
        "vendor_checks",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("org_id", sa.String(length=36), sa.ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vendor", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("requested_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )

    # Attestations
    op.create_table(
        "attestations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("check_id", sa.Integer, sa.ForeignKey("vendor_checks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("issued_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("valid_until", sa.DateTime(), nullable=True),
        sa.Column("revocation_status", sa.String(length=16), nullable=False, server_default="Active"),
        sa.Column("signature", sa.String(length=512), nullable=True),
    )

    # Composite passports
    op.create_table(
        "composite_passports",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("org_id", sa.String(length=36), sa.ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="draft"),
        sa.Column("issued_at", sa.DateTime(), nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("chain_anchor", sa.String(length=255), nullable=True),
    )

    # Verification requests
    op.create_table(
        "verification_requests",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("bank_id", sa.Integer, sa.ForeignKey("banks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("passport_id", sa.Integer, sa.ForeignKey("composite_passports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requested_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=True),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("audited_by", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )

    # Existing tables: add linking columns to align with ERD without breaking app
    bind = op.get_bind()
    users_cols = _column_names(bind, "users")
    with op.batch_alter_table("users") as batch:
        if "org_id" not in users_cols:
            batch.add_column(sa.Column("org_id", sa.String(length=36), sa.ForeignKey("organisations.id"), nullable=True))
        if "is_active" not in users_cols:
            batch.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.sql.expression.true()))

    subs_cols = _column_names(bind, "submissions")
    with op.batch_alter_table("submissions") as batch:
        if "org_id" not in subs_cols:
            batch.add_column(sa.Column("org_id", sa.String(length=36), sa.ForeignKey("organisations.id"), nullable=True))
        if "status" not in subs_cols:
            batch.add_column(sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"))

    docs_cols = _column_names(bind, "documents")
    with op.batch_alter_table("documents") as batch:
        if "hash" not in docs_cols:
            batch.add_column(sa.Column("hash", sa.String(length=128), nullable=True))
        if "storage_ref" not in docs_cols:
            batch.add_column(sa.Column("storage_ref", sa.String(length=1024), nullable=True))


def downgrade() -> None:
    # Revert additions to existing tables first (drop if present)
    bind = op.get_bind()

    docs_cols = _column_names(bind, "documents")
    with op.batch_alter_table("documents") as batch:
        if "storage_ref" in docs_cols:
            batch.drop_column("storage_ref")
        if "hash" in docs_cols:
            batch.drop_column("hash")

    subs_cols = _column_names(bind, "submissions")
    with op.batch_alter_table("submissions") as batch:
        if "status" in subs_cols:
            batch.drop_column("status")
        if "org_id" in subs_cols:
            batch.drop_column("org_id")

    users_cols = _column_names(bind, "users")
    with op.batch_alter_table("users") as batch:
        if "is_active" in users_cols:
            batch.drop_column("is_active")
        if "org_id" in users_cols:
            batch.drop_column("org_id")

    # Drop new tables (reverse order of dependencies)
    op.drop_table("verification_requests")
    op.drop_table("composite_passports")
    op.drop_table("attestations")
    op.drop_table("vendor_checks")
    op.drop_table("banks")
    op.drop_table("organisations")
