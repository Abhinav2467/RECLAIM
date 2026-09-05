"""add raw_webhook_events

Revision ID: 0002_raw_webhook_events
Revises: 0001_initial_tables
Create Date: 2026-09-02 00:00:00.000001
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0002_raw_webhook_events'
down_revision = '0001_initial_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'raw_webhook_events',
        sa.Column('id', sa.BigInteger(), sa.Identity(start=1, cycle=False), primary_key=True),
        sa.Column('merchant_id', sa.BigInteger(), sa.ForeignKey('merchants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider', sa.String(length=64), nullable=False),
        sa.Column('provider_event_id', sa.String(length=255), nullable=False),
        sa.Column('signature_header', sa.String(length=1024), nullable=True),
        sa.Column('raw_body', sa.LargeBinary(), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('headers', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default=sa.text("'pending'")),
        sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.UniqueConstraint('merchant_id', 'provider', 'provider_event_id', name='uq_raw_webhook_events_merchant_provider_event'),
    )
    op.create_index('ix_raw_webhook_events_merchant_id', 'raw_webhook_events', ['merchant_id'])
    op.create_index('ix_raw_webhook_events_status', 'raw_webhook_events', ['status'])


def downgrade() -> None:
    op.drop_index('ix_raw_webhook_events_status', table_name='raw_webhook_events')
    op.drop_index('ix_raw_webhook_events_merchant_id', table_name='raw_webhook_events')
    op.drop_table('raw_webhook_events')
