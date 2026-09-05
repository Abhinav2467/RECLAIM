import uuid
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import select, delete

from app.main import app
from app.db.models import Merchant, Customer, Order, Payment, RecoveryCase, ExecutionRecord, RecoveryAuditEvent, User
from app.core.security import hash_password

client = TestClient(app)


def _get_auth_client_for_merchant(db_session, merchant_id: int, name: str) -> TestClient:
    m = db_session.get(Merchant, merchant_id)
    if not m:
        m = Merchant(id=merchant_id, name=name)
        db_session.add(m)
        db_session.commit()
    
    email = f"sse_m{merchant_id}_{uuid.uuid4().hex[:6]}@example.com"
    u = User(merchant_id=merchant_id, email=email, password_hash=hash_password("Pass123!"))
    db_session.add(u)
    db_session.commit()

    tc = TestClient(app)
    tc.post("/api/auth/login", json={"email": email, "password": "Pass123!"})
    return tc


def test_sse_stream_unknown_case_returns_404(db_session):
    tc = _get_auth_client_for_merchant(db_session, 900, "SSE Unknown Merchant")
    res = tc.get("/api/recovery-cases/999999/stream")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"]


def test_sse_stream_initial_events_and_terminal_behavior(db_session):
    tc = _get_auth_client_for_merchant(db_session, 901, "SSE Test Merchant")

    # Clean existing test data for merchant 901
    existing_cases = db_session.execute(select(RecoveryCase).where(RecoveryCase.merchant_id == 901)).scalars().all()
    for c_item in existing_cases:
        db_session.execute(delete(RecoveryAuditEvent).where(RecoveryAuditEvent.recovery_case_id == c_item.id))
        db_session.execute(delete(ExecutionRecord).where(ExecutionRecord.recovery_case_id == c_item.id))
        db_session.delete(c_item)
    db_session.commit()

    c = db_session.execute(select(Customer).where(Customer.merchant_id == 901, Customer.external_id == "cust_sse_1")).scalars().first()
    if not c:
        c = Customer(merchant_id=901, external_id="cust_sse_1", name="SSE Customer", email="sse@example.com")
        db_session.add(c)
        db_session.commit()

    o = db_session.execute(select(Order).where(Order.merchant_id == 901, Order.external_id == "ord_sse_1")).scalars().first()
    if not o:
        o = Order(merchant_id=901, customer_id=c.id, external_id="ord_sse_1", amount_total=Decimal("100.00"), currency="USD")
        db_session.add(o)
        db_session.commit()

    p = db_session.execute(select(Payment).where(Payment.merchant_id == 901, Payment.provider_payment_id == "pay_sse_1")).scalars().first()
    if not p:
        p = Payment(merchant_id=901, customer_id=c.id, order_id=o.id, provider_payment_id="pay_sse_1", amount=Decimal("100.00"), currency="USD", status="authorized", provider_state="authorized")
        db_session.add(p)
        db_session.commit()

    rc = RecoveryCase(merchant_id=901, customer_id=c.id, order_id=o.id, payment_id=p.id, status="RECOVERED", reason="AUTHORIZATION_STALE", recoverable_amount=Decimal("100.00"), currency="USD")
    db_session.add(rc)
    db_session.commit()

    ev1 = RecoveryAuditEvent(recovery_case_id=rc.id, event_type="CASE_CREATED", status="DETECTED", message="Case created")
    ev2 = RecoveryAuditEvent(recovery_case_id=rc.id, event_type="RECOVERY_VERIFIED", status="RECOVERED", message="Case verified")
    db_session.add_all([ev1, ev2])
    db_session.commit()

    # Stream from start (cursor = 0)
    res = tc.get(f"/api/recovery-cases/{rc.id}/stream")
    assert res.status_code == 200
    assert "text/event-stream" in res.headers["content-type"]

    body = res.text
    assert f'"id": {ev1.id}' in body
    assert "event: audit_event" in body or "event: initial_state" in body
    assert "CASE_CREATED" in body
    assert f'"id": {ev2.id}' in body
    assert "RECOVERY_VERIFIED" in body
    assert "event: terminal" in body
    assert '"terminal": true' in body


def test_sse_stream_last_event_id_cursor_resume(db_session):
    tc = _get_auth_client_for_merchant(db_session, 902, "SSE Cursor Merchant")

    # Clean existing test data for merchant 902
    existing_cases = db_session.execute(select(RecoveryCase).where(RecoveryCase.merchant_id == 902)).scalars().all()
    for c_item in existing_cases:
        db_session.execute(delete(RecoveryAuditEvent).where(RecoveryAuditEvent.recovery_case_id == c_item.id))
        db_session.execute(delete(ExecutionRecord).where(ExecutionRecord.recovery_case_id == c_item.id))
        db_session.delete(c_item)
    db_session.commit()

    c = db_session.execute(select(Customer).where(Customer.merchant_id == 902, Customer.external_id == "cust_sse_2")).scalars().first()
    if not c:
        c = Customer(merchant_id=902, external_id="cust_sse_2", name="SSE Customer 2", email="sse2@example.com")
        db_session.add(c)
        db_session.commit()

    o = db_session.execute(select(Order).where(Order.merchant_id == 902, Order.external_id == "ord_sse_2")).scalars().first()
    if not o:
        o = Order(merchant_id=902, customer_id=c.id, external_id="ord_sse_2", amount_total=Decimal("50.00"), currency="USD")
        db_session.add(o)
        db_session.commit()

    p = db_session.execute(select(Payment).where(Payment.merchant_id == 902, Payment.provider_payment_id == "pay_sse_2")).scalars().first()
    if not p:
        p = Payment(merchant_id=902, customer_id=c.id, order_id=o.id, provider_payment_id="pay_sse_2", amount=Decimal("50.00"), currency="USD", status="authorized", provider_state="authorized")
        db_session.add(p)
        db_session.commit()

    rc = RecoveryCase(merchant_id=902, customer_id=c.id, order_id=o.id, payment_id=p.id, status="NO_ACTION", reason="PAYMENT_FAILURE", recoverable_amount=Decimal("0.00"), currency="USD")
    db_session.add(rc)
    db_session.commit()

    ev1 = RecoveryAuditEvent(recovery_case_id=rc.id, event_type="CASE_CREATED", status="DETECTED", message="Created")
    ev2 = RecoveryAuditEvent(recovery_case_id=rc.id, event_type="DECISION_MADE", status="NO_ACTION", message="No action")
    db_session.add_all([ev1, ev2])
    db_session.commit()

    # Pass Last-Event-ID header set to ev1.id so ev1 is skipped and only ev2 & terminal are streamed
    res = tc.get(f"/api/recovery-cases/{rc.id}/stream", headers={"Last-Event-ID": str(ev1.id)})
    assert res.status_code == 200

    body = res.text
    # ev1 should not be delivered
    assert f'"id": {ev1.id}' not in body
    # ev2 should be delivered
    assert f'"id": {ev2.id}' in body
    assert "DECISION_MADE" in body
    # terminal should be delivered
    assert "event: terminal" in body
