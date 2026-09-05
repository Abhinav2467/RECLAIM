import json
import datetime

from app.db.session import SessionLocal
from app.db.models import RawWebhookEvent, Payment
from app.events.types import RevenueEventType


def post_webhook(client, body: bytes, signature: str, event_id: str):
    headers = {
        "Content-Type": "application/json",
        "X-Razorpay-Signature": signature,
        "x-razorpay-event-id": event_id,
    }
    return client.post("/webhooks/providers/razorpay", data=body, headers=headers)


def test_valid_webhook_reconciles_payment(client, sign):
    db = SessionLocal()
    try:
        # create payment
        from app.db.models import Merchant
        m = db.get(Merchant, 1)
        p = Payment(merchant_id=1, provider_payment_id="pay_proc", amount=100, currency="USD")
        db.add(p)
        db.commit()

        body = json.dumps({
            "event": "payment.captured",
            "created_at": int(datetime.datetime.now(tz=datetime.timezone.utc).timestamp()),
            "payload": {"payment": {"entity": {"id": "pay_proc", "created_at": int(datetime.datetime.now(tz=datetime.timezone.utc).timestamp())}}}
        }).encode("utf-8")
        sig = sign(body)
        resp = post_webhook(client, body, sig, "proc-001")
        assert resp.status_code == 200
        j = resp.json()
        assert j["status"] == "processed"
        assert j["provider_event_id"] == "proc-001"
        # payment should be updated
        db.refresh(p)
        assert p.provider_state == "captured"
        assert p.provider_event_id == "proc-001"
    finally:
        db.close()


def test_duplicate_webhook_no_second_reconcile(client, sign):
    db = SessionLocal()
    try:
        p = Payment(merchant_id=1, provider_payment_id="dup_pay", amount=50, currency="USD")
        db.add(p)
        db.commit()

        body = json.dumps({
            "event": "payment.captured",
            "created_at": int(datetime.datetime.now(tz=datetime.timezone.utc).timestamp()),
            "payload": {"payment": {"entity": {"id": "dup_pay", "created_at": int(datetime.datetime.now(tz=datetime.timezone.utc).timestamp())}}}
        }).encode("utf-8")
        sig = sign(body)
        r1 = post_webhook(client, body, sig, "dup-001")
        assert r1.status_code == 200 and r1.json()["status"] == "processed"
        # second identical request
        r2 = post_webhook(client, body, sig, "dup-001")
        assert r2.status_code == 200 and r2.json()["status"] == "duplicate"
        # only one RawWebhookEvent exists
        q = db.query(RawWebhookEvent).filter(RawWebhookEvent.provider_event_id == "dup-001")
        assert q.count() == 1
    finally:
        db.close()


def test_unsupported_event_persists_but_fails_processing(client, sign):
    db = SessionLocal()
    try:
        body = json.dumps({"event": "refund.processed", "created_at": int(datetime.datetime.now(tz=datetime.timezone.utc).timestamp())}).encode("utf-8")
        sig = sign(body)
        r = post_webhook(client, body, sig, "unsup-001")
        assert r.status_code == 200
        j = r.json()
        assert j["status"] == "failed"
        # RawWebhookEvent exists and is marked failed
        raw = db.query(RawWebhookEvent).filter(RawWebhookEvent.provider_event_id == "unsup-001").one()
        assert raw.status == "failed"
    finally:
        db.close()


def test_provider_event_id_flows(client, sign):
    db = SessionLocal()
    try:
        p = Payment(merchant_id=1, provider_payment_id="flow_pay", amount=20, currency="USD")
        db.add(p)
        db.commit()

        body = json.dumps({
            "event": "payment.captured",
            "created_at": int(datetime.datetime.now(tz=datetime.timezone.utc).timestamp()),
            "payload": {"payment": {"entity": {"id": "flow_pay", "created_at": int(datetime.datetime.now(tz=datetime.timezone.utc).timestamp())}}}
        }).encode("utf-8")
        sig = sign(body)
        r = post_webhook(client, body, sig, "flow-001")
        assert r.status_code == 200
        j = r.json()
        assert j["provider_event_id"] == "flow-001"
        # RawWebhookEvent has provider_event_id
        raw = db.query(RawWebhookEvent).filter(RawWebhookEvent.provider_event_id == "flow-001").one()
        assert raw.provider_event_id == "flow-001"
        # Payment provider_event_id updated
        db.refresh(p)
        assert p.provider_event_id == "flow-001"
    finally:
        db.close()


def test_stale_webhook_does_not_regress(client, sign):
    db = SessionLocal()
    try:
        # create payment with future provider_state_at
        future = datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(minutes=10)
        p = Payment(merchant_id=1, provider_payment_id="stale_pay", amount=10, currency="USD", provider_state="captured", provider_state_at=future, provider_event_id="evt_future")
        db.add(p)
        db.commit()

        # send an older event
        old_ts = int((datetime.datetime.now(tz=datetime.timezone.utc)).timestamp())
        body = json.dumps({
            "event": "payment.failed",
            "created_at": old_ts,
            "payload": {"payment": {"entity": {"id": "stale_pay", "created_at": old_ts}}}
        }).encode("utf-8")
        sig = sign(body)
        r = post_webhook(client, body, sig, "stale-001")
        assert r.status_code == 200
        j = r.json()
        assert j["status"] == "processed"
        # payment should remain captured
        db.refresh(p)
        assert p.provider_state == "captured"
        assert p.provider_event_id == "evt_future"
    finally:
        db.close()
