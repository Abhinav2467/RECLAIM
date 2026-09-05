import json
import hmac
import hashlib

from app.db.session import SessionLocal
from app.db.models import RawWebhookEvent


def post_webhook(client, body: bytes, signature: str, event_id: str):
    headers = {
        "Content-Type": "application/json",
        "X-Razorpay-Signature": signature,
        "x-razorpay-event-id": event_id,
    }
    return client.post("/webhooks/providers/razorpay", data=body, headers=headers)


def count_events(event_id: str):
    db = SessionLocal()
    try:
        q = db.query(RawWebhookEvent).filter(RawWebhookEvent.provider_event_id == event_id)
        return q.count()
    finally:
        db.close()


def test_valid_webhook_accepted_and_persisted(client, sign):
    body = json.dumps({"event": "payment.captured", "data": {}}).encode("utf-8")
    sig = sign(body)
    resp = post_webhook(client, body, sig, "test-valid-001")
    assert resp.status_code == 200
    assert resp.json()["status"] == "processed"
    assert count_events("test-valid-001") == 1


def test_duplicate_webhook_returns_duplicate(client, sign):
    body = json.dumps({"event": "payment.captured", "data": {}}).encode("utf-8")
    sig = sign(body)
    r1 = post_webhook(client, body, sig, "test-dup-001")
    assert r1.status_code == 200 and r1.json()["status"] == "processed"
    r2 = post_webhook(client, body, sig, "test-dup-001")
    assert r2.status_code == 200 and r2.json()["status"] == "duplicate"
    assert count_events("test-dup-001") == 1


def test_invalid_signature_returns_401(client):
    body = json.dumps({"event": "payment.captured"}).encode("utf-8")
    # incorrect signature
    sig = "deadbeef"
    resp = post_webhook(client, body, sig, "test-invalid-001")
    assert resp.status_code == 401
    assert count_events("test-invalid-001") == 0


def test_missing_event_id_returns_400(client, sign):
    body = json.dumps({"event": "payment.captured"}).encode("utf-8")
    sig = sign(body)
    headers = {"Content-Type": "application/json", "X-Razorpay-Signature": sig}
    resp = client.post("/webhooks/providers/razorpay", data=body, headers=headers)
    assert resp.status_code == 400
    assert count_events("") == 0


def test_malformed_json_with_valid_signature_returns_400(client, sign):
    body = b'{"event": "payment.captured"'  # malformed
    sig = sign(body)
    resp = post_webhook(client, body, sig, "test-malformed-001")
    assert resp.status_code == 400
    assert count_events("test-malformed-001") == 0
