from decimal import Decimal

from app.events.types import RevenueEvent, RevenueEventType
from app.events.reconciler import reconcile_revenue_event
from app.db.session import SessionLocal
from app.db.models import Payment, Order
import datetime


def make_event(event_type, merchant_id=1, payment_id=None, order_id=None, raw_event_id=None, provider_event_id="evt1", occurred_at=None):
    return RevenueEvent(
        event_id=provider_event_id,
        provider_event_id=provider_event_id,
        provider="razorpay",
        merchant_id=merchant_id,
        event_type=event_type,
        occurred_at=occurred_at,
        occurred_at_source="provider_event" if occurred_at is not None else None,
        payment_id=payment_id,
        order_id=order_id,
        customer_id=None,
        amount=None,
        currency=None,
        payment_status=None,
        failure_code=None,
        failure_reason=None,
        raw_event_id=raw_event_id,
    )


def test_forward_payment_transition(db_session):
    db = db_session
    # create payment row without status
    p = Payment(merchant_id=1, provider_payment_id="p_fwd", amount=Decimal("10.00"), currency="USD", status=None)
    db.add(p)
    db.commit()

    ev = make_event(RevenueEventType.PAYMENT_AUTHORIZED, payment_id="p_fwd", provider_event_id="evt_fwd", occurred_at=datetime.datetime.now(tz=datetime.timezone.utc))
    res = reconcile_revenue_event(db, ev)
    assert res.payment_changed
    assert res.payment_resulting_state == "authorized"


def test_repeated_same_state_event_idempotent(db_session):
    db = db_session
    p = Payment(merchant_id=1, provider_payment_id="p_dup", amount=Decimal("5.00"), currency="USD", status=None)
    db.add(p)
    db.commit()

    now = datetime.datetime.now(tz=datetime.timezone.utc)
    ev = make_event(RevenueEventType.PAYMENT_AUTHORIZED, payment_id="p_dup", provider_event_id="evt_dup", occurred_at=now)
    r1 = reconcile_revenue_event(db, ev)
    r2 = reconcile_revenue_event(db, ev)
    assert r1.payment_changed
    assert not r2.payment_changed
    assert r2.payment_resulting_state == "authorized"


def test_stale_payment_after_captured(db_session):
    db = db_session
    # stored payment has a provider_state_at in future; incoming older should be stale
    future_ts = datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(minutes=10)
    p = Payment(merchant_id=1, provider_payment_id="p_stale", amount=Decimal("20.00"), currency="USD", status="captured", provider_state="captured", provider_state_at=future_ts, provider_event_id="evt_existing")
    db.add(p)
    db.commit()

    older_ts = datetime.datetime.now(tz=datetime.timezone.utc)
    ev = make_event(RevenueEventType.PAYMENT_FAILURE, payment_id="p_stale", provider_event_id="evt_old", occurred_at=older_ts)
    res = reconcile_revenue_event(db, ev)
    assert res.outcome == "stale"
    assert not res.payment_changed


def test_forward_order_transition_updates_payment_and_marks_order_paid(db_session):
    db = db_session
    # create order and payment linked to it
    order = Order(merchant_id=1, external_id="ord1", amount_total=Decimal("100.00"), currency="USD")
    db.add(order)
    db.commit()
    p = Payment(merchant_id=1, provider_payment_id="p_ord", amount=Decimal("100.00"), currency="USD", status=None, order_id=order.id)
    db.add(p)
    db.commit()

    # ORDER_PAID with order_id but no payment_id should not return 'missing'
    ev_no_payment = make_event(RevenueEventType.ORDER_PAID, payment_id=None, order_id="ord1", provider_event_id="evt_ord_no_payment", occurred_at=datetime.datetime.now(tz=datetime.timezone.utc))
    res_no_payment = reconcile_revenue_event(db, ev_no_payment)
    assert res_no_payment.outcome != "missing"
    assert res_no_payment.order_previous_state in ("open", "paid")

    # Capturing the linked payment should change derived order state from open -> paid
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    ev_capture = make_event(RevenueEventType.PAYMENT_CAPTURED, payment_id="p_ord", order_id="ord1", provider_event_id="evt_ord_cap", occurred_at=now)
    res_cap = reconcile_revenue_event(db, ev_capture)
    assert res_cap.payment_changed
    assert res_cap.payment_resulting_state == "captured"
    # derived order state should move to paid after capture
    assert res_cap.order_resulting_state == "paid"
    assert res_cap.order_previous_state in ("open", "paid")


def test_missing_payment_and_order_handled(db_session):
    db = db_session
    ev = make_event(RevenueEventType.PAYMENT_CAPTURED, payment_id="nonexistent", provider_event_id="evt_miss", occurred_at=datetime.datetime.now(tz=datetime.timezone.utc))
    res = reconcile_revenue_event(db, ev)
    assert res.outcome == "missing"


def test_idempotent_reprocessing(db_session):
    db = db_session
    p = Payment(merchant_id=1, provider_payment_id="p_idem", amount=Decimal("1.00"), currency="USD", status=None)
    db.add(p)
    db.commit()

    now = datetime.datetime.now(tz=datetime.timezone.utc)
    ev = make_event(RevenueEventType.PAYMENT_CAPTURED, payment_id="p_idem", provider_event_id="evt_idem", occurred_at=now)
    r1 = reconcile_revenue_event(db, ev)
    # replay with same provider_event_id
    r2 = reconcile_revenue_event(db, ev)
    assert r1.payment_changed
    assert not r2.payment_changed


def test_already_paid_order_another_payment_capture_no_change(db_session):
    db = db_session
    # create order and one already-captured payment
    order = Order(merchant_id=1, external_id="ord_paid", amount_total=Decimal("50.00"), currency="USD")
    db.add(order)
    db.commit()

    p1 = Payment(merchant_id=1, provider_payment_id="p1", amount=Decimal("30.00"), currency="USD", status=None, order_id=order.id, provider_state="captured", provider_state_at=datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(minutes=5), provider_event_id="evt_p1")
    p2 = Payment(merchant_id=1, provider_payment_id="p2", amount=Decimal("20.00"), currency="USD", status=None, order_id=order.id)
    db.add_all([p1, p2])
    db.commit()

    # capture p2 now; order was already paid, so order_changed should be False
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    ev = make_event(RevenueEventType.PAYMENT_CAPTURED, payment_id="p2", order_id="ord_paid", provider_event_id="evt_p2_cap", occurred_at=now)
    res = reconcile_revenue_event(db, ev)
    assert res.payment_changed
    assert res.payment_resulting_state == "captured"
    assert res.order_previous_state == "paid"
    assert res.order_resulting_state == "paid"
    assert res.order_changed is False


def test_open_order_first_capture_changes_order(db_session):
    db = db_session
    order = Order(merchant_id=1, external_id="ord_open", amount_total=Decimal("40.00"), currency="USD")
    db.add(order)
    db.commit()

    p = Payment(merchant_id=1, provider_payment_id="p_open", amount=Decimal("40.00"), currency="USD", status=None, order_id=order.id)
    db.add(p)
    db.commit()

    now = datetime.datetime.now(tz=datetime.timezone.utc)
    ev = make_event(RevenueEventType.PAYMENT_CAPTURED, payment_id="p_open", order_id="ord_open", provider_event_id="evt_open_cap", occurred_at=now)
    res = reconcile_revenue_event(db, ev)
    assert res.payment_changed
    assert res.order_previous_state == "open"
    assert res.order_resulting_state == "paid"
    assert res.order_changed is True


def test_authorization_failure_does_not_mark_paid(db_session):
    db = db_session
    order = Order(merchant_id=1, external_id="ord_auth", amount_total=Decimal("25.00"), currency="USD")
    db.add(order)
    db.commit()

    p = Payment(merchant_id=1, provider_payment_id="p_auth", amount=Decimal("25.00"), currency="USD", status=None, order_id=order.id)
    db.add(p)
    db.commit()

    now = datetime.datetime.now(tz=datetime.timezone.utc)
    ev_auth = make_event(RevenueEventType.PAYMENT_AUTHORIZED, payment_id="p_auth", order_id="ord_auth", provider_event_id="evt_auth", occurred_at=now)
    res_auth = reconcile_revenue_event(db, ev_auth)
    assert res_auth.payment_changed
    assert res_auth.payment_resulting_state == "authorized"
    assert res_auth.order_previous_state == "open"
    assert res_auth.order_resulting_state == "open"
    assert res_auth.order_changed is False


def test_order_paid_derived_consistent_with_payment_reconciliation(db_session):
    db = db_session
    order = Order(merchant_id=1, external_id="ord_consistent", amount_total=Decimal("60.00"), currency="USD")
    db.add(order)
    db.commit()

    p = Payment(merchant_id=1, provider_payment_id="p_cons", amount=Decimal("60.00"), currency="USD", status=None, order_id=order.id)
    db.add(p)
    db.commit()

    # ORDER_PAID with no payment should derive order as open (no captured payments)
    ev_order_paid = make_event(RevenueEventType.ORDER_PAID, payment_id=None, order_id="ord_consistent", provider_event_id="evt_ord_cons", occurred_at=datetime.datetime.now(tz=datetime.timezone.utc))
    res_ord = reconcile_revenue_event(db, ev_order_paid)
    assert res_ord.order_previous_state == "open"
    assert res_ord.order_resulting_state == "open"

    # Now capture the payment and ensure order becomes paid
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    ev_cap = make_event(RevenueEventType.PAYMENT_CAPTURED, payment_id="p_cons", order_id="ord_consistent", provider_event_id="evt_cons_cap", occurred_at=now)
    res_cap = reconcile_revenue_event(db, ev_cap)
    assert res_cap.order_previous_state == "open"
    assert res_cap.order_resulting_state == "paid"
    assert res_cap.order_changed is True
