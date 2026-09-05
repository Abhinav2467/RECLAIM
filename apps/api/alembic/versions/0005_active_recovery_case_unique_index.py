"""add partial unique index for active recovery cases

Revision ID: 0005_active_case_unique_index
Revises: 0004_recovery_audit_execution
Create Date: 2026-09-03 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0005_active_case_unique_index'
down_revision = '0004_recovery_audit_execution'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        'uq_active_recovery_case_payment',
        'recovery_cases',
        ['merchant_id', 'payment_id'],
        unique=True,
        postgresql_where=sa.text("payment_id IS NOT NULL AND status NOT IN ('RECOVERED', 'NO_ACTION', 'NOT_RECOVERABLE', 'FAILED', 'ABORTED')"),
        sqlite_where=sa.text("payment_id IS NOT NULL AND status NOT IN ('RECOVERED', 'NO_ACTION', 'NOT_RECOVERABLE', 'FAILED', 'ABORTED')"),
    )
    op.create_index(
        'uq_active_recovery_case_order',
        'recovery_cases',
        ['merchant_id', 'order_id'],
        unique=True,
        postgresql_where=sa.text("order_id IS NOT NULL AND status NOT IN ('RECOVERED', 'NO_ACTION', 'NOT_RECOVERABLE', 'FAILED', 'ABORTED')"),
        sqlite_where=sa.text("order_id IS NOT NULL AND status NOT IN ('RECOVERED', 'NO_ACTION', 'NOT_RECOVERABLE', 'FAILED', 'ABORTED')"),
    )


def downgrade() -> None:
    op.drop_index('uq_active_recovery_case_payment', table_name='recovery_cases')
    op.drop_index('uq_active_recovery_case_order', table_name='recovery_cases')
