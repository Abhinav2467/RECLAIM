"""add users table for merchant authentication

Revision ID: 0006_users_table
Revises: 0005_active_case_unique_index
Create Date: 2026-09-04 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '0006_users_table'
down_revision = '0005_active_case_unique_index'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger(), sa.Identity(start=1, cycle=False), primary_key=True),
        sa.Column('merchant_id', sa.BigInteger(), sa.ForeignKey('merchants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('email', sa.String(length=320), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_users_merchant_id', 'users', ['merchant_id'])
    op.create_index('ix_users_email', 'users', ['email'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_users_email', table_name='users')
    op.drop_index('ix_users_merchant_id', table_name='users')
    op.drop_table('users')
