import json
from decimal import Decimal
import pytest

from app.integrations.razorpay_normalizer import normalize_raw_webhook, RevenueEventParseError
from app.events.types import RevenueEventType
import datetime


def make_payload(event, entity):
    return {"event": event, "payload": {event.split(".")[0]: {"entity": entity}}}


def test_payment_failed_mapping():
    entity = {"id": "pay_1", "amount": "100.50", "currency": "INR", "status": "failed", "error_code": "E001", "error_description": "insufficient funds"}
    payload = make_payload("payment.failed", entity)
    ev = normalize_raw_webhook(payload, merchant_id=1, provider="razorpay", raw_event_id=10, provider_event_id="evt_10")
    assert ev.event_type == RevenueEventType.PAYMENT_FAILURE
    assert ev.payment_id == "pay_1"
    assert ev.amount == Decimal("100.50")
    assert ev.currency == "INR"
    assert ev.failure_code == "E001"
    assert ev.failure_reason == "insufficient funds"


def test_payment_authorized_mapping():
    entity = {"id": "pay_2", "amount": 200, "currency": "USD", "status": "authorized"}
    payload = make_payload("payment.authorized", entity)
    ev = normalize_raw_webhook(payload, merchant_id=2, provider="razorpay", raw_event_id=11, provider_event_id="evt_11")
    assert ev.event_type == RevenueEventType.PAYMENT_AUTHORIZED
    assert ev.payment_id == "pay_2"
    assert ev.amount == Decimal("200")
    assert ev.currency == "USD"


def test_payment_captured_mapping():
    entity = {"id": "pay_3", "amount": "300.00", "currency": "EUR", "status": "captured"}
    payload = make_payload("payment.captured", entity)
    ev = normalize_raw_webhook(payload, merchant_id=3, provider="razorpay", raw_event_id=12, provider_event_id="evt_12")
    assert ev.event_type == RevenueEventType.PAYMENT_CAPTURED
    assert ev.payment_id == "pay_3"
    assert ev.amount == Decimal("300.00")
    assert ev.currency == "EUR"


def test_order_paid_mapping():
    entity = {"id": "order_1", "amount": "500", "currency": "INR"}
    payload = make_payload("order.paid", entity)
    ev = normalize_raw_webhook(payload, merchant_id=4, provider="razorpay", raw_event_id=13, provider_event_id="evt_13")
    assert ev.event_type == RevenueEventType.ORDER_PAID
    assert ev.order_id == "order_1"
    assert ev.amount == Decimal("500")


def test_missing_optional_fields_remain_none():
    entity = {"id": "pay_4"}
    payload = make_payload("payment.captured", entity)
    ev = normalize_raw_webhook(payload, merchant_id=5, provider="razorpay", raw_event_id=14, provider_event_id="evt_14")
    assert ev.payment_id == "pay_4"
    assert ev.amount is None
    assert ev.currency is None
    assert ev.customer_id is None


def test_unsupported_event_raises():
    payload = {"event": "invoice.paid", "payload": {"invoice": {"entity": {"id": "inv_1"}}}}
    with pytest.raises(RevenueEventParseError):
        normalize_raw_webhook(payload, merchant_id=1, provider="razorpay", raw_event_id=20, provider_event_id="evt_20")


def test_malformed_missing_event_field_raises():
    payload = {"payload": {"payment": {"entity": {"id": "p_1"}}}}
    with pytest.raises(RevenueEventParseError):
        normalize_raw_webhook(payload, merchant_id=1, provider="razorpay", raw_event_id=21, provider_event_id="evt_21")


def test_integration_normalizer_with_rawwebhook(db_session):
    # Create a synthetic raw payload as would be persisted in RawWebhookEvent.payload
    entity = {"id": "pay_int_1", "amount": 123.45, "currency": "USD", "status": "failed", "error_code": "C123", "error_description": "timeout"}
    payload = make_payload("payment.failed", entity)

    # Simulate RawWebhookEvent persisted row: pass payload dict and id
    ev = normalize_raw_webhook(payload, merchant_id=1, provider="razorpay", raw_event_id=999, provider_event_id="evt_999")
    assert ev.raw_event_id == 999
    assert ev.payment_id == "pay_int_1"
    assert ev.failure_code == "C123"


def test_created_at_precedence_and_conversion():
    # top-level created_at should take precedence and be converted to tz-aware datetime
    entity = {"id": "pay_ts", "amount": 100, "currency": "USD", "created_at": 1600000000}
    payload = {"event": "payment.captured", "created_at": 1600000100, "payload": {"payment": {"entity": entity}}}
    ev = normalize_raw_webhook(payload, merchant_id=1, provider="razorpay", raw_event_id=200, provider_event_id="evt_200")
    assert ev.occurred_at is not None
    assert isinstance(ev.occurred_at, datetime.datetime)
    assert ev.occurred_at.tzinfo is not None
    # top-level takes precedence: 1600000100
    assert ev.occurred_at == datetime.datetime.fromtimestamp(1600000100, tz=datetime.timezone.utc)


def test_invalid_timestamp_does_not_crash_and_leaves_none():
    entity = {"id": "pay_bad_ts", "amount": 50}
    payload = {"event": "payment.failed", "created_at": "not-an-int", "payload": {"payment": {"entity": entity}}}
    ev = normalize_raw_webhook(payload, merchant_id=1, provider="razorpay", raw_event_id=201, provider_event_id="evt_201")
    assert ev.occurred_at is None
