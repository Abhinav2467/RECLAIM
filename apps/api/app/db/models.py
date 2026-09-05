from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy import Integer, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import LargeBinary
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.domain.states import RecoveryStatus


class Merchant(Base):
    __tablename__ = "merchants"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=True, name="metadata")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    customers = relationship("Customer", back_populates="merchant", lazy="selectin")
    orders = relationship("Order", back_populates="merchant", lazy="selectin")
    users = relationship("User", back_populates="merchant", lazy="selectin")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    merchant = relationship("Merchant", back_populates="users", lazy="selectin")


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(255), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=True)
    email: Mapped[str] = mapped_column(String(320), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    merchant = relationship("Merchant", back_populates="customers", lazy="selectin")
    orders = relationship("Order", back_populates="customer", lazy="selectin")
    __table_args__ = (
        UniqueConstraint("merchant_id", "external_id", name="uq_customers_merchant_external"),
    )


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    external_id: Mapped[str] = mapped_column(String(255), nullable=True)

    amount_total: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    merchant = relationship("Merchant", back_populates="orders", lazy="selectin")
    customer = relationship("Customer", back_populates="orders", lazy="selectin")
    payments = relationship("Payment", back_populates="order", lazy="selectin")
    __table_args__ = (
        UniqueConstraint("merchant_id", "external_id", name="uq_orders_merchant_external"),
    )


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True)

    provider_payment_id: Mapped[str] = mapped_column(String(255), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=True, index=True)
    provider_payload: Mapped[dict] = mapped_column(JSONB, nullable=True)
    # Provider-observed state and provenance
    provider_state: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    provider_state_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_event_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    provider_raw_event_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("raw_webhook_events.id", ondelete="SET NULL"), nullable=True, index=True)
    provider_failure_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    provider_failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    __table_args__ = (
        UniqueConstraint("merchant_id", "provider_payment_id", name="uq_payments_merchant_provider"),
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    order = relationship("Order", back_populates="payments", lazy="selectin")


class RecoveryCase(Base):
    __tablename__ = "recovery_cases"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id", ondelete="SET NULL"), nullable=True)

    status: Mapped[RecoveryStatus] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # lifecycle fields added for decision/execution/verification
    context_version: Mapped[int] = mapped_column(Integer, nullable=True)
    diagnosis: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    diagnosis_confidence: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    recommended_action: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    policy_decision: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    execution_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    verification_outcome: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    recoverable_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)

    reason: Mapped[str] = mapped_column(Text, nullable=True)
    details: Mapped[dict] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_recovery_cases_merchant", "merchant_id"),
        Index("ix_recovery_cases_customer", "customer_id"),
        Index("ix_recovery_cases_order", "order_id"),
        Index("ix_recovery_cases_payment", "payment_id"),
        Index("ix_recovery_cases_status", "status"),
        Index(
            "uq_active_recovery_case_payment",
            "merchant_id",
            "payment_id",
            unique=True,
            postgresql_where=text("payment_id IS NOT NULL AND status NOT IN ('RECOVERED', 'NO_ACTION', 'NOT_RECOVERABLE', 'FAILED', 'ABORTED')"),
            sqlite_where=text("payment_id IS NOT NULL AND status NOT IN ('RECOVERED', 'NO_ACTION', 'NOT_RECOVERABLE', 'FAILED', 'ABORTED')"),
        ),
        Index(
            "uq_active_recovery_case_order",
            "merchant_id",
            "order_id",
            unique=True,
            postgresql_where=text("order_id IS NOT NULL AND status NOT IN ('RECOVERED', 'NO_ACTION', 'NOT_RECOVERABLE', 'FAILED', 'ABORTED')"),
            sqlite_where=text("order_id IS NOT NULL AND status NOT IN ('RECOVERED', 'NO_ACTION', 'NOT_RECOVERABLE', 'FAILED', 'ABORTED')"),
        ),
    )

    merchant = relationship("Merchant", lazy="joined")
    customer = relationship("Customer", lazy="joined")
    order = relationship("Order", lazy="joined")
    payment = relationship("Payment", lazy="joined")


class RawWebhookEvent(Base):
    __tablename__ = "raw_webhook_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_event_id: Mapped[str] = mapped_column(String(255), nullable=False)
    signature_header: Mapped[str] = mapped_column(String(1024), nullable=True)
    raw_body: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    headers: Mapped[dict] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="pending")
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("merchant_id", "provider", "provider_event_id", name="uq_raw_webhook_events_merchant_provider_event"),
        Index("ix_raw_webhook_events_merchant_id", "merchant_id"),
        Index("ix_raw_webhook_events_status", "status"),
    )

    merchant = relationship("Merchant", lazy="joined")


class ExecutionRecord(Base):
    __tablename__ = "execution_records"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    recovery_case_id: Mapped[Optional[int]] = mapped_column(ForeignKey("recovery_cases.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    provider_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    result: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        UniqueConstraint("action", "idempotency_key", name="uq_execution_action_idempotency"),
        Index("ix_execution_recovery_case", "recovery_case_id"),
    )


class RecoveryAuditEvent(Base):
    __tablename__ = "recovery_audit_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    recovery_case_id: Mapped[int] = mapped_column(ForeignKey("recovery_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    event_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    actor: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    action: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    evidence: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_audit_recovery_case", "recovery_case_id"),
    )
