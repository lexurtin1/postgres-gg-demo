"""add_submission_and_document

I create two tables:
- submissions: one row per multi-file upload session (the 'flight record').
- documents: one row per uploaded file (each 'bag'), linked to a submission.

I keep this migration intentionally simple so it works in any dev environment.
"""

from alembic import op  # I use Alembic's operations helpers to define DDL
import sqlalchemy as sa  # I use SQLAlchemy types for columns

# I set the Alembic identifiers so Alembic knows revision ordering.
revision = '9b1a2c3d4e5f'
down_revision = '736238865f6f'
branch_labels = None
depends_on = None


def upgrade():
    # I create the submissions table first so documents can reference it.
    op.create_table(
        'submissions',
        sa.Column('id', sa.Integer(), primary_key=True),  # I use a simple integer PK
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),  # I link to users
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),  # I timestamp creation
    )

    # I create the documents table which points to submissions.
    op.create_table(
        'documents',
        sa.Column('id', sa.Integer(), primary_key=True),  # I use a simple integer PK
        sa.Column('submission_id', sa.Integer(), sa.ForeignKey('submissions.id', ondelete='CASCADE'), nullable=False),  # I link to submissions
        sa.Column('filename', sa.String(length=512), nullable=False),  # I store the original filename
        sa.Column('stored_path', sa.String(length=1024), nullable=False),  # I store the path where I saved the file
        sa.Column('document_type', sa.String(length=64), nullable=False),  # I store the inferred document type
        sa.Column('uploaded_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),  # I timestamp upload time
    )

    # I add simple indexes to help list/filter documents later.
    op.create_index('ix_documents_document_type', 'documents', ['document_type'])
    op.create_index('ix_documents_uploaded_at', 'documents', ['uploaded_at'])


def downgrade():
    # I drop indexes before dropping the table to be explicit and clear.
    op.drop_index('ix_documents_uploaded_at', table_name='documents')
    op.drop_index('ix_documents_document_type', table_name='documents')

    # I drop tables in reverse order of creation due to foreign keys.
    op.drop_table('documents')
    op.drop_table('submissions')

