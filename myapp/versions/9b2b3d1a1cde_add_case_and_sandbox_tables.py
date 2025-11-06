"""Add Case, CaseDecision, Request, ApiKey, WebhookEndpoint, AuditEvent tables"""

from alembic import op
import sqlalchemy as sa

# Alembic identifiers
revision = '9b2b3d1a1cde'
down_revision = '736238865f6f'
branch_labels = None
depends_on = None


def _has_table(bind, name: str) -> bool:
    inspector = sa.inspect(bind)
    return name in inspector.get_table_names()


def upgrade():
    bind = op.get_bind()

    if not _has_table(bind, 'cases'):
        op.create_table(
            'cases',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('org_id', sa.String(length=36), sa.ForeignKey('organisations.id')),
            sa.Column('status', sa.String(length=24), nullable=False, server_default='running'),
            sa.Column('sla_due_at', sa.DateTime()),
            sa.Column('risk_flags', sa.String(length=255)),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )

    if not _has_table(bind, 'case_decisions'):
        op.create_table(
            'case_decisions',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('case_id', sa.Integer(), sa.ForeignKey('cases.id'), nullable=False),
            sa.Column('actor_user_id', sa.Integer(), sa.ForeignKey('users.id')),
            sa.Column('decision', sa.String(length=16), nullable=False),
            sa.Column('reason', sa.String(length=255)),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )

    if not _has_table(bind, 'requests'):
        op.create_table(
            'requests',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('org_id', sa.String(length=36), sa.ForeignKey('organisations.id')),
            sa.Column('case_id', sa.Integer(), sa.ForeignKey('cases.id')),
            sa.Column('type', sa.String(length=50)),
            sa.Column('reason_code', sa.String(length=50)),
            sa.Column('message', sa.String(length=512)),
            sa.Column('status', sa.String(length=24), nullable=False, server_default='open'),
            sa.Column('due_at', sa.DateTime()),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )

    if not _has_table(bind, 'api_keys'):
        op.create_table(
            'api_keys',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('org_id', sa.String(length=36), sa.ForeignKey('organisations.id')),
            sa.Column('prefix', sa.String(length=16), nullable=False, unique=True),
            sa.Column('secret', sa.String(length=64), nullable=False),
            sa.Column('status', sa.String(length=16), nullable=False, server_default='active'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )

    if not _has_table(bind, 'webhook_endpoints'):
        op.create_table(
            'webhook_endpoints',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('org_id', sa.String(length=36), sa.ForeignKey('organisations.id')),
            sa.Column('url', sa.String(length=512)),
            sa.Column('signing_secret', sa.String(length=64)),
            sa.Column('status', sa.String(length=16), nullable=False, server_default='enabled'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )

    if not _has_table(bind, 'audit_events'):
        op.create_table(
            'audit_events',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('case_id', sa.Integer(), sa.ForeignKey('cases.id')),
            sa.Column('actor_user_id', sa.Integer(), sa.ForeignKey('users.id')),
            sa.Column('event_type', sa.String(length=50), nullable=False),
            sa.Column('data_json', sa.Text()),
            sa.Column('correlation_id', sa.String(length=64)),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )


def downgrade():
    for name in ['audit_events', 'webhook_endpoints', 'api_keys', 'requests', 'case_decisions', 'cases']:
        op.execute(f'DROP TABLE IF EXISTS {name} CASCADE;')

