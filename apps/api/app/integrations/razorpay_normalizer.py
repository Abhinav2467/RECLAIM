from decimal import Decimal
from typing import Any, Dict, Optional
import datetime

from app.events.types import RevenueEvent, RevenueEventType, RevenueEventParseError


def _get_resource(payload: Dict[str, Any], resource_name: str) -> Optional[Dict[str, Any]]:
    # Razorpay wraps resource under payload -> <resource> -> entity
    p = payload.get("payload") or {}
    res = p.get(resource_name)
    if isinstance(res, dict) and "entity" in res:
        return res.get("entity")
    # Sometimes tests may pass resource directly under payload
    if resource_name in payload:
        candidate = payload.get(resource_name)
        if isinstance(candidate, dict):
            return candidate.get("entity") or candidate
    return None


def normalize_raw_webhook(raw_payload: Dict[str, Any], merchant_id: int, provider: str, raw_event_id: int, provider_event_id: Optional[str] = None) -> RevenueEvent:
    """Normalize a Razorpay webhook payload dict into a RevenueEvent.

    This function is strict: unsupported event types raise RevenueEventParseError.
    Missing optional fields remain None.
    """
    event = raw_payload.get("event")
    if not event:
        raise RevenueEventParseError("missing event type")

    # Map known events
    mapping = {
        "payment.failed": RevenueEventType.PAYMENT_FAILURE,
        "payment.authorized": RevenueEventType.PAYMENT_AUTHORIZED,
        "payment.captured": RevenueEventType.PAYMENT_CAPTURED,
        "order.paid": RevenueEventType.ORDER_PAID,
    }

    if event not in mapping:
        raise RevenueEventParseError(f"unsupported razorpay event type: {event}")

    event_type = mapping[event]

    # Extract resource entity depending on event
    resource = None
    if event.startswith("payment"):
        resource = _get_resource(raw_payload, "payment")
    elif event.startswith("order"):
        resource = _get_resource(raw_payload, "order")

    # Event identifier: use explicit provider_event_id when supplied. Never
    # default to payment/order ids as canonical event id.
    event_id = None
    if provider_event_id:
        event_id = provider_event_id
    else:
        # fall back to any top-level id if present (rare)
        event_id = raw_payload.get("id") or raw_payload.get("event_id")
    if not event_id:
        # as last resort, use the event name so value is not empty (but caller
        # should supply provider_event_id for idempotency)
        event_id = raw_payload.get("event")

    payment_id = None
    order_id = None
    customer_id = None
    amount = None
    currency = None
    payment_status = None
    failure_code = None
    failure_reason = None
    occurred_at = None
    occurred_at_source = None

    if resource and isinstance(resource, dict):
        # For payment resources, `id` is the payment id. For order resources,
        # `id` is the order id. Handle order.paid explicitly to set order_id.
        if event_type == RevenueEventType.ORDER_PAID:
            order_id = resource.get("id")
            payment_id = None
        else:
            payment_id = resource.get("id")
            order_id = resource.get("order_id")
        customer_id = resource.get("customer_id")
        # Amount: keep provider value as-is and convert to Decimal when numeric/str
        raw_amount = resource.get("amount")
        if raw_amount is not None:
            try:
                amount = Decimal(str(raw_amount))
            except Exception:
                amount = None
        currency = resource.get("currency")
        payment_status = resource.get("status")
        failure_code = resource.get("error_code") or resource.get("failure_code")
        failure_reason = resource.get("error_description") or resource.get("failure_reason")
        # prefer top-level event created_at as provider-observed event time
        top_created = raw_payload.get("created_at")
        resource_created = resource.get("created_at") or resource.get("date")
        # Helper: convert epoch seconds -> tz-aware UTC datetime
        def _to_dt(val):
            try:
                if val is None:
                    return None
                # accept strings or numbers; convert to int seconds
                ts = int(val)
                return datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
            except Exception:
                return None

        dt_top = _to_dt(top_created)
        if dt_top:
            occurred_at = dt_top
            occurred_at_source = "provider_event"
        else:
            dt_res = _to_dt(resource_created)
            if dt_res:
                occurred_at = dt_res
                occurred_at_source = "resource_created"

    return RevenueEvent(
        event_id=str(event_id),
        provider=provider,
        merchant_id=merchant_id,
        event_type=event_type,
        occurred_at=occurred_at,
        occurred_at_source=occurred_at_source,
        provider_event_id=provider_event_id,
        payment_id=payment_id,
        order_id=order_id,
        customer_id=customer_id,
        amount=amount,
        currency=currency,
        payment_status=payment_status,
        failure_code=failure_code,
        failure_reason=failure_reason,
        raw_event_id=raw_event_id,
    )
