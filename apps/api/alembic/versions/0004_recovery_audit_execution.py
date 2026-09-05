"""add recovery audit events and execution records

Revision ID: 0004_recovery_audit_execution
Revises: 0003_add_payment_provider_fields
Create Date: 2026-09-03 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0004_recovery_audit_execution'
down_revision = '0003_add_payment_provider_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # add columns to recovery_cases
    op.add_column('recovery_cases', sa.Column('context_version', sa.Integer(), nullable=True))
    op.add_column('recovery_cases', sa.Column('diagnosis', sa.String(length=255), nullable=True))
    op.add_column('recovery_cases', sa.Column('diagnosis_confidence', sa.String(length=64), nullable=True))
    op.add_column('recovery_cases', sa.Column('recommended_action', sa.String(length=255), nullable=True))
    op.add_column('recovery_cases', sa.Column('policy_decision', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('recovery_cases', sa.Column('execution_id', sa.String(length=255), nullable=True))
    op.add_column('recovery_cases', sa.Column('verification_outcome', sa.String(length=64), nullable=True))
    op.add_column('recovery_cases', sa.Column('recoverable_amount', sa.Numeric(18,4), nullable=True))
    op.add_column('recovery_cases', sa.Column('currency', sa.String(length=8), nullable=True))

    # create execution_records table
    op.create_table(
        'execution_records',
        sa.Column('id', sa.BigInteger(), sa.Identity(start=1, cycle=False), primary_key=True),
        sa.Column('recovery_case_id', sa.BigInteger(), sa.ForeignKey('recovery_cases.id', ondelete='SET NULL'), nullable=True),
        sa.Column('action', sa.String(length=255), nullable=False),
        sa.Column('idempotency_key', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=64), nullable=True),
        sa.Column('provider_reference', sa.String(length=255), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_index('ix_execution_recovery_case', 'execution_records', ['recovery_case_id'])
    op.create_unique_constraint('uq_execution_action_idempotency', 'execution_records', ['action', 'idempotency_key'])

    # create recovery_audit_events table
    op.create_table(
        'recovery_audit_events',
        sa.Column('id', sa.BigInteger(), sa.Identity(start=1, cycle=False), primary_key=True),
        sa.Column('recovery_case_id', sa.BigInteger(), sa.ForeignKey('recovery_cases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('event_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('actor', sa.String(length=255), nullable=True),
        sa.Column('action', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=64), nullable=True),
        sa.Column('idempotency_key', sa.String(length=255), nullable=True),
        sa.Column('evidence', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('message', sa.Text(), nullable=True),
    )
    op.create_index('ix_audit_recovery_case', 'recovery_audit_events', ['recovery_case_id'])


def downgrade() -> None:
    op.drop_index('ix_audit_recovery_case', table_name='recovery_audit_events')
    op.drop_table('recovery_audit_events')

    op.drop_constraint('uq_execution_action_idempotency', 'execution_records', type_='unique')
    op.drop_index('ix_execution_recovery_case', table_name='execution_records')
    op.drop_table('execution_records')

    op.drop_column('recovery_cases', 'currency')
    op.drop_column('recovery_cases', 'recoverable_amount')
    op.drop_column('recovery_cases', 'verification_outcome')
    op.drop_column('recovery_cases', 'execution_id')
    op.drop_column('recovery_cases', 'policy_decision')
    op.drop_column('recovery_cases', 'recommended_action')
    op.drop_column('recovery_cases', 'diagnosis_confidence')
    op.drop_column('recovery_cases', 'diagnosis')
    op.drop_column('recovery_cases', 'context_version')
