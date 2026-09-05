from enum import StrEnum


class RevenueEventType(StrEnum):
    PAYMENT_FAILURE = "PAYMENT_FAILURE"
    PAYMENT_AUTHORIZED = "PAYMENT_AUTHORIZED"
    PAYMENT_CAPTURED = "PAYMENT_CAPTURED"
    ORDER_PAID = "ORDER_PAID"
    OFFER_DISCREPANCY = "OFFER_DISCREPANCY"
    INVOICE_OVERDUE = "INVOICE_OVERDUE"


from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
import datetime


@dataclass
class RevenueEvent:
    event_id: str
    provider: str
    merchant_id: int
    event_type: RevenueEventType
    # timezone-aware UTC datetime when the provider observed/created the event
    occurred_at: Optional[datetime.datetime] = None
    # provenance of occurred_at: provider_event | resource_created | received_at_fallback | None
    occurred_at_source: Optional[str] = None
    # explicit provider event id (e.g. x-razorpay-event-id). When supplied,
    # `event_id` should equal this value.
    provider_event_id: Optional[str] = None
    payment_id: Optional[str] = None
    order_id: Optional[str] = None
    customer_id: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    payment_status: Optional[str] = None
    failure_code: Optional[str] = None
    failure_reason: Optional[str] = None
    raw_event_id: Optional[int] = None


class RevenueEventParseError(Exception):
    """Raised when provider payload cannot be normalized into a RevenueEvent."""
    pass


from dataclasses import dataclass
from typing import Optional


@dataclass
class ReconciliationResult:
    raw_event_id: Optional[int]
    provider_event_id: Optional[str]
    provider_observed_at: Optional[datetime.datetime]
    provider_observed_confidence: Optional[str]
    payment_id: Optional[str]
    order_id: Optional[str]
    payment_previous_state: Optional[str]
    payment_resulting_state: Optional[str]
    payment_changed: bool
    payment_ignored: bool
    payment_conflict: bool
    conflict_reason: Optional[str]
    order_previous_state: Optional[str]
    order_resulting_state: Optional[str]
    order_changed: bool
    outcome: Optional[str]
    message: Optional[str] = None
