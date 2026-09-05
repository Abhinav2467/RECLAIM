"""add payment provider fields

Revision ID: 0003_add_payment_provider_fields
Revises: 0002_raw_webhook_events
Create Date: 2026-09-02 00:00:00.000010
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '0003_add_payment_provider_fields'
down_revision = '0002_raw_webhook_events'
branch_labels = None
depends_on = None

_TABLE = "payments"
_FK_NAME = "fk_payments_provider_raw_event"
_ADDED_BY_COMMENT = "alembic:0003_add_payment_provider_fields"

_PROVIDER_COLUMNS = (
    ("provider_state", sa.String(length=64)),
    ("provider_state_at", sa.DateTime(timezone=True)),
    ("provider_event_id", sa.String(length=255)),
    ("provider_raw_event_id", sa.BigInteger()),
    ("provider_failure_code", sa.String(length=64)),
    ("provider_failure_reason", sa.Text()),
)


def _column_names(inspector) -> set[str]:
    return {col["name"] for col in inspector.get_columns(_TABLE)}


def _has_provider_raw_event_fk(inspector) -> bool:
    for fk in inspector.get_foreign_keys(_TABLE):
        if fk.get("name") == _FK_NAME:
            return True
        if (
            fk.get("constrained_columns") == ["provider_raw_event_id"]
            and fk.get("referred_table") == "raw_webhook_events"
        ):
            return True
    return False


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing = _column_names(inspector)

    for name, col_type in _PROVIDER_COLUMNS:
        if name in existing:
            continue
        op.add_column(_TABLE, sa.Column(name, col_type, nullable=True))
        # Marker so downgrade drops only columns this revision actually created.
        op.execute(
            sa.text(
                f"COMMENT ON COLUMN {_TABLE}.{name} IS '{_ADDED_BY_COMMENT}'"
            )
        )

    inspector = inspect(bind)
    if not _has_provider_raw_event_fk(inspector):
        op.create_foreign_key(
            _FK_NAME,
            _TABLE,
            "raw_webhook_events",
            ["provider_raw_event_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if any(fk.get("name") == _FK_NAME for fk in inspector.get_foreign_keys(_TABLE)):
        op.drop_constraint(_FK_NAME, _TABLE, type_="foreignkey")

    inspector = inspect(bind)
    comments = {col["name"]: col.get("comment") for col in inspector.get_columns(_TABLE)}
    for name, _col_type in reversed(_PROVIDER_COLUMNS):
        if comments.get(name) == _ADDED_BY_COMMENT:
            op.drop_column(_TABLE, name)
