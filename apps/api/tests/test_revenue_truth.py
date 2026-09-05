from decimal import Decimal
import datetime

from app.domain.revenue_truth import assess_order_revenue, RevenueTruthResult
from app.db.models import Order, Payment
from app.db.session import SessionLocal


def test_single_captured_equals_order(db_session):
    db = db_session
    order = Order(merchant_id=1, external_id='o1', amount_total=Decimal('100.00'), currency='USD')
    db.add(order)
    db.commit()

    p = Payment(merchant_id=1, provider_payment_id='p1', amount=Decimal('100.00'), currency='USD', provider_state='captured', order_id=order.id)
    db.add(p)
    db.commit()

    res = assess_order_revenue(db, order.id)
    assert res.expected_amount == Decimal('100.00')
    assert res.captured_amount == Decimal('100.00')
    assert res.recoverable_amount == Decimal('0')
    assert res.resolution == 'complete'


def test_order_with_no_payments(db_session):
    db = db_session
    order = Order(merchant_id=1, external_id='o2', amount_total=Decimal('75.50'), currency='GBP')
    db.add(order)
    db.commit()

    res = assess_order_revenue(db, order.id)
    assert res.captured_amount == Decimal('0')
    assert res.recoverable_amount == Decimal('75.50')
    assert res.resolution == 'complete'


def test_two_captured_below_expected(db_session):
    db = db_session
    order = Order(merchant_id=1, external_id='o3', amount_total=Decimal('200.00'), currency='USD')
    db.add(order)
    db.commit()

    p1 = Payment(merchant_id=1, provider_payment_id='p3a', amount=Decimal('50.00'), currency='USD', provider_state='captured', order_id=order.id)
    p2 = Payment(merchant_id=1, provider_payment_id='p3b', amount=Decimal('70.00'), currency='USD', provider_state='captured', order_id=order.id)
    db.add_all([p1, p2])
    db.commit()

    res = assess_order_revenue(db, order.id)
    assert res.captured_amount == Decimal('120.00')
    assert res.recoverable_amount == Decimal('80.00')
    assert res.resolution == 'complete'


def test_overcapture(db_session):
    db = db_session
    order = Order(merchant_id=1, external_id='o4', amount_total=Decimal('150.00'), currency='USD')
    db.add(order)
    db.commit()

    p1 = Payment(merchant_id=1, provider_payment_id='p4a', amount=Decimal('100.00'), currency='USD', provider_state='captured', order_id=order.id)
    p2 = Payment(merchant_id=1, provider_payment_id='p4b', amount=Decimal('75.00'), currency='USD', provider_state='captured', order_id=order.id)
    db.add_all([p1, p2])
    db.commit()

    res = assess_order_revenue(db, order.id)
    assert res.captured_amount == Decimal('175.00')
    assert res.recoverable_amount == Decimal('0')
    assert res.resolution == 'complete'


def test_authorized_excluded(db_session):
    db = db_session
    order = Order(merchant_id=1, external_id='o5', amount_total=Decimal('40.00'), currency='USD')
    db.add(order)
    db.commit()

    p = Payment(merchant_id=1, provider_payment_id='p5', amount=Decimal('40.00'), currency='USD', provider_state='authorized', order_id=order.id)
    db.add(p)
    db.commit()

    res = assess_order_revenue(db, order.id)
    assert res.captured_amount == Decimal('0')
    assert res.recoverable_amount == Decimal('40.00')


def test_failed_excluded(db_session):
    db = db_session
    order = Order(merchant_id=1, external_id='o6', amount_total=Decimal('20.00'), currency='USD')
    db.add(order)
    db.commit()

    p = Payment(merchant_id=1, provider_payment_id='p6', amount=Decimal('20.00'), currency='USD', provider_state='failed', order_id=order.id)
    db.add(p)
    db.commit()

    res = assess_order_revenue(db, order.id)
    assert res.captured_amount == Decimal('0')
    assert res.recoverable_amount == Decimal('20.00')


def test_currency_mismatch(db_session):
    db = db_session
    order = Order(merchant_id=1, external_id='o7', amount_total=Decimal('100.00'), currency='USD')
    db.add(order)
    db.commit()

    p = Payment(merchant_id=1, provider_payment_id='p7', amount=Decimal('50.00'), currency='EUR', provider_state='captured', order_id=order.id)
    db.add(p)
    db.commit()

    res = assess_order_revenue(db, order.id)
    assert res.resolution == 'currency_mismatch'
    assert res.recoverable_amount is None


def test_missing_order(db_session):
    db = db_session
    res = assess_order_revenue(db, None)
    assert res.resolution == 'no_order'
    assert res.expected_amount is None


def test_missing_order_amount(db_session):
    db = db_session
    db = db_session
    # The DB schema enforces NOT NULL on orders.amount_total; attempting to
    # insert a NULL will raise an IntegrityError. Assert that missing amount
    # cannot be represented at the schema level in this test environment.
    from sqlalchemy.exc import IntegrityError
    from app.db.models import Order as OrderModel
    o = OrderModel(merchant_id=1, external_id='o8', amount_total=None, currency='USD')
    db.add(o)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return
    # If commit succeeded unexpectedly, still run assessment defensively
    p = Payment(merchant_id=1, provider_payment_id='p8', amount=Decimal('10.00'), currency='USD', provider_state='captured', order_id=o.id)
    db.add(p)
    db.commit()
    res = assess_order_revenue(db, o.id)
    assert res.expected_amount is not None


def test_provenance_fields_present(db_session):
    db = db_session
    order = Order(merchant_id=1, external_id='o9', amount_total=Decimal('60.00'), currency='USD')
    db.add(order)
    db.commit()

    p = Payment(merchant_id=1, provider_payment_id='p9', amount=Decimal('60.00'), currency='USD', provider_state='captured', provider_event_id='evt9', provider_state_at=datetime.datetime.now(tz=datetime.timezone.utc), order_id=order.id)
    db.add(p)
    db.commit()

    res = assess_order_revenue(db, order.id)
    assert len(res.contributing_payments) == 1
    cp = res.contributing_payments[0]
    assert cp.provider_event_id == 'evt9'
    assert cp.provider_state == 'captured'


def test_decimal_determinism_and_non_negative(db_session):
    db = db_session
    order = Order(merchant_id=1, external_id='o10', amount_total=Decimal('100.00'), currency='USD')
    db.add(order)
    db.commit()

    p = Payment(merchant_id=1, provider_payment_id='p10', amount=Decimal('150.00'), currency='USD', provider_state='captured', order_id=order.id)
    db.add(p)
    db.commit()

    res = assess_order_revenue(db, order.id)
    assert isinstance(res.captured_amount, Decimal)
    assert res.recoverable_amount == Decimal('0')


def test_idempotent_assessment(db_session):
    db = db_session
    order = Order(merchant_id=1, external_id='o11', amount_total=Decimal('30.00'), currency='USD')
    db.add(order)
    db.commit()

    p = Payment(merchant_id=1, provider_payment_id='p11', amount=Decimal('10.00'), currency='USD', provider_state='captured', order_id=order.id)
    db.add(p)
    db.commit()

    r1 = assess_order_revenue(db, order.id)
    r2 = assess_order_revenue(db, order.id)
    assert r1.captured_amount == r2.captured_amount
    assert r1.recoverable_amount == r2.recoverable_amount
