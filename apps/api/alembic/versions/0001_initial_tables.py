"""initial tables

Revision ID: 0001_initial_tables
Revises: 
Create Date: 2026-09-02 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001_initial_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # merchants
    op.create_table(
        'merchants',
        sa.Column('id', sa.BigInteger(), sa.Identity(start=1, cycle=False), primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_merchants_name', 'merchants', ['name'])

    # customers
    op.create_table(
        'customers',
        sa.Column('id', sa.BigInteger(), sa.Identity(start=1, cycle=False), primary_key=True),
        sa.Column('merchant_id', sa.BigInteger(), sa.ForeignKey('merchants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('external_id', sa.String(length=255), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('email', sa.String(length=320), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('merchant_id', 'external_id', name='uq_customers_merchant_external'),
    )
    op.create_index('ix_customers_merchant_id', 'customers', ['merchant_id'])
    op.create_index('ix_customers_email', 'customers', ['email'])

    # orders
    op.create_table(
        'orders',
        sa.Column('id', sa.BigInteger(), sa.Identity(start=1, cycle=False), primary_key=True),
        sa.Column('merchant_id', sa.BigInteger(), sa.ForeignKey('merchants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('customer_id', sa.BigInteger(), sa.ForeignKey('customers.id', ondelete='SET NULL'), nullable=True),
        sa.Column('external_id', sa.String(length=255), nullable=True),
        sa.Column('amount_total', sa.Numeric(18, 4), nullable=False),
        sa.Column('currency', sa.String(length=8), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('merchant_id', 'external_id', name='uq_orders_merchant_external'),
    )
    op.create_index('ix_orders_merchant_id', 'orders', ['merchant_id'])
    op.create_index('ix_orders_customer_id', 'orders', ['customer_id'])

    # payments
    op.create_table(
        'payments',
        sa.Column('id', sa.BigInteger(), sa.Identity(start=1, cycle=False), primary_key=True),
        sa.Column('merchant_id', sa.BigInteger(), sa.ForeignKey('merchants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('customer_id', sa.BigInteger(), sa.ForeignKey('customers.id', ondelete='SET NULL'), nullable=True),
        sa.Column('order_id', sa.BigInteger(), sa.ForeignKey('orders.id', ondelete='SET NULL'), nullable=True),
        sa.Column('provider_payment_id', sa.String(length=255), nullable=True),
        sa.Column('amount', sa.Numeric(18, 4), nullable=False),
        sa.Column('currency', sa.String(length=8), nullable=False),
        sa.Column('status', sa.String(length=64), nullable=True),
        sa.Column('provider_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('merchant_id', 'provider_payment_id', name='uq_payments_merchant_provider'),
    )
    op.create_index('ix_payments_merchant_id', 'payments', ['merchant_id'])
    op.create_index('ix_payments_customer_id', 'payments', ['customer_id'])
    op.create_index('ix_payments_order_id', 'payments', ['order_id'])
    op.create_index('ix_payments_status', 'payments', ['status'])

    # recovery_cases
    op.create_table(
        'recovery_cases',
        sa.Column('id', sa.BigInteger(), sa.Identity(start=1, cycle=False), primary_key=True),
        sa.Column('merchant_id', sa.BigInteger(), sa.ForeignKey('merchants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('customer_id', sa.BigInteger(), sa.ForeignKey('customers.id', ondelete='SET NULL'), nullable=True),
        sa.Column('order_id', sa.BigInteger(), sa.ForeignKey('orders.id', ondelete='SET NULL'), nullable=True),
        sa.Column('payment_id', sa.BigInteger(), sa.ForeignKey('payments.id', ondelete='SET NULL'), nullable=True),
        sa.Column('status', sa.String(length=64), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default="1"),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_recovery_cases_merchant', 'recovery_cases', ['merchant_id'])
    op.create_index('ix_recovery_cases_customer', 'recovery_cases', ['customer_id'])
    op.create_index('ix_recovery_cases_order', 'recovery_cases', ['order_id'])
    op.create_index('ix_recovery_cases_payment', 'recovery_cases', ['payment_id'])
    op.create_index('ix_recovery_cases_status', 'recovery_cases', ['status'])


def downgrade() -> None:
    op.drop_index('ix_recovery_cases_status', table_name='recovery_cases')
    op.drop_index('ix_recovery_cases_payment', table_name='recovery_cases')
    op.drop_index('ix_recovery_cases_order', table_name='recovery_cases')
    op.drop_index('ix_recovery_cases_customer', table_name='recovery_cases')
    op.drop_index('ix_recovery_cases_merchant', table_name='recovery_cases')
    op.drop_table('recovery_cases')

    op.drop_index('ix_payments_status', table_name='payments')
    op.drop_index('ix_payments_order_id', table_name='payments')
    op.drop_index('ix_payments_customer_id', table_name='payments')
    op.drop_index('ix_payments_merchant_id', table_name='payments')
    op.drop_table('payments')

    op.drop_index('ix_orders_customer_id', table_name='orders')
    op.drop_index('ix_orders_merchant_id', table_name='orders')
    op.drop_table('orders')

    op.drop_index('ix_customers_email', table_name='customers')
    op.drop_index('ix_customers_merchant_id', table_name='customers')
    op.drop_table('customers')

    op.drop_index('ix_merchants_name', table_name='merchants')
    op.drop_table('merchants')
