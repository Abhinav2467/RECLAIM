from datetime import timedelta
import datetime
from decimal import Decimal

from app.domain.revenue_truth import assess_order_revenue
from app.domain.diagnosis import diagnose, DiagnosisResult
from app.db.models import Order, Payment


def test_failed_payment_triggers_payment_failure(db_session):
    db = db_session
    order = Order(merchant_id=1, external_id='d1', amount_total=Decimal('10.00'), currency='USD')
    db.add(order)
    db.commit()
    p = Payment(merchant_id=1, provider_payment_id='dp1', amount=Decimal('10.00'), currency='USD', provider_state='failed', provider_event_id='fevt', provider_state_at=datetime.datetime.now(tz=datetime.timezone.utc), order_id=order.id, provider_failure_code='card_declined')
    db.add(p)
    db.commit()

    rt = assess_order_revenue(db, order.id)
    before_count = db.query(Payment).count()
    res = diagnose(db, rt, order_id=order.id, payment_id=p.id, auth_stale_after=timedelta(seconds=30), abandonment_after=timedelta(hours=1))
    after_count = db.query(Payment).count()
    assert res.diagnosis == 'PAYMENT_FAILURE'
    assert res.confidence == 'high'
    assert 'provider_failure_code' in res.evidence or 'contributing_payments' in res.evidence
    assert before_count == after_count


def test_failed_payment_missing_provenance_medium_confidence(db_session):
    db = db_session
    order = Order(merchant_id=1, external_id='d2', amount_total=Decimal('20.00'), currency='USD')
    db.add(order)
    db.commit()
    p = Payment(merchant_id=1, provider_payment_id='dp2', amount=Decimal('20.00'), currency='USD', provider_state='failed', provider_event_id=None, provider_state_at=None, order_id=order.id)
    db.add(p)
    db.commit()

    rt = assess_order_revenue(db, order.id)
    res = diagnose(db, rt, order_id=order.id, payment_id=p.id, auth_stale_after=timedelta(seconds=30), abandonment_after=timedelta(hours=1))
    assert res.diagnosis == 'PAYMENT_FAILURE'
    assert res.confidence == 'medium'


def test_fresh_authorization_not_stale(db_session):
    db = db_session
    order = Order(merchant_id=1, external_id='d3', amount_total=Decimal('50.00'), currency='USD')
    db.add(order)
    db.commit()
    p = Payment(merchant_id=1, provider_payment_id='dp3', amount=Decimal('50.00'), currency='USD', provider_state='authorized', provider_state_at=datetime.datetime.now(tz=datetime.timezone.utc), order_id=order.id)
    db.add(p)
    db.commit()

    rt = assess_order_revenue(db, order.id)
    res = diagnose(db, rt, order_id=order.id, payment_id=p.id, auth_stale_after=timedelta(minutes=5), abandonment_after=timedelta(hours=1))
    assert res.diagnosis == 'UNKNOWN'


def test_stale_authorization_triggers_authorization_stale(db_session):
    db = db_session
    order = Order(merchant_id=1, external_id='d4', amount_total=Decimal('60.00'), currency='USD')
    db.add(order)
    db.commit()
    past = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(hours=1)
    p = Payment(merchant_id=1, provider_payment_id='dp4', amount=Decimal('60.00'), currency='USD', provider_state='authorized', provider_state_at=past, provider_event_id='ae1', order_id=order.id)
    db.add(p)
    db.commit()

    rt = assess_order_revenue(db, order.id)
    res = diagnose(db, rt, order_id=order.id, payment_id=p.id, auth_stale_after=timedelta(minutes=30), abandonment_after=timedelta(hours=1))
    assert res.diagnosis == 'AUTHORIZATION_STALE'
    assert res.confidence == 'high'


def test_stale_authorization_but_already_captured_not_stale(db_session):
    db = db_session
    order = Order(merchant_id=1, external_id='d5', amount_total=Decimal('70.00'), currency='USD')
    db.add(order)
    db.commit()
    past = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(hours=2)
    p = Payment(merchant_id=1, provider_payment_id='dp5', amount=Decimal('70.00'), currency='USD', provider_state='captured', provider_state_at=past, provider_event_id='cap1', order_id=order.id)
    db.add(p)
    db.commit()

    rt = assess_order_revenue(db, order.id)
    res = diagnose(db, rt, order_id=order.id, payment_id=p.id, auth_stale_after=timedelta(minutes=30), abandonment_after=timedelta(hours=1))
    assert res.diagnosis == 'UNKNOWN'


def test_old_unpaid_order_abandonment(db_session):
    db = db_session
    old = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=2)
    order = Order(merchant_id=1, external_id='d6', amount_total=Decimal('80.00'), currency='USD', created_at=old)
    db.add(order)
    db.commit()

    rt = assess_order_revenue(db, order.id)
    res = diagnose(db, rt, order_id=order.id, payment_id=None, auth_stale_after=timedelta(minutes=30), abandonment_after=timedelta(days=1))
    assert res.diagnosis == 'CHECKOUT_ABANDONMENT'
    assert res.confidence == 'medium'


def test_old_order_with_authorized_payment_not_abandonment(db_session):
    db = db_session
    old = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=3)
    order = Order(merchant_id=1, external_id='d7', amount_total=Decimal('90.00'), currency='USD', created_at=old)
    db.add(order)
    db.commit()
    p = Payment(merchant_id=1, provider_payment_id='dp7', amount=Decimal('90.00'), currency='USD', provider_state='authorized', provider_state_at=datetime.datetime.now(tz=datetime.timezone.utc), order_id=order.id)
    db.add(p)
    db.commit()

    rt = assess_order_revenue(db, order.id)
    res = diagnose(db, rt, order_id=order.id, payment_id=None, auth_stale_after=timedelta(minutes=30), abandonment_after=timedelta(days=1))
    assert res.diagnosis == 'UNKNOWN'


def test_revenue_truth_unknown_leads_unknown(db_session):
    db = db_session
    res = diagnose(db, None, order_id=None, payment_id=None, auth_stale_after=timedelta(minutes=30), abandonment_after=timedelta(days=1))
    assert res.diagnosis == 'UNKNOWN'


def test_currency_mismatch_leads_unknown(db_session):
    db = db_session
    order = Order(merchant_id=1, external_id='d8', amount_total=Decimal('100.00'), currency='USD')
    db.add(order)
    db.commit()
    p = Payment(merchant_id=1, provider_payment_id='dp8', amount=Decimal('50.00'), currency='EUR', provider_state='captured', order_id=order.id)
    db.add(p)
    db.commit()

    rt = assess_order_revenue(db, order.id)
    res = diagnose(db, rt, order_id=order.id, payment_id=None, auth_stale_after=timedelta(minutes=30), abandonment_after=timedelta(days=1))
    assert res.diagnosis == 'UNKNOWN'


def test_missing_order_leads_unknown(db_session):
    db = db_session
    rt = assess_order_revenue(db, None)
    res = diagnose(db, rt, order_id=None, payment_id=None, auth_stale_after=timedelta(minutes=30), abandonment_after=timedelta(days=1))
    assert res.diagnosis == 'UNKNOWN'


def test_insufficient_evidence_unknown(db_session):
    db = db_session
    order = Order(merchant_id=1, external_id='d9', amount_total=Decimal('110.00'), currency='USD')
    db.add(order)
    db.commit()
    # no payments, created recently
    rt = assess_order_revenue(db, order.id)
    res = diagnose(db, rt, order_id=order.id, payment_id=None, auth_stale_after=timedelta(days=1), abandonment_after=timedelta(days=7))
    assert res.diagnosis == 'UNKNOWN'


def test_suggested_actions_and_evidence_fields(db_session):
    db = db_session
    order = Order(merchant_id=1, external_id='d10', amount_total=Decimal('120.00'), currency='USD')
    db.add(order)
    db.commit()
    p = Payment(merchant_id=1, provider_payment_id='dp10', amount=Decimal('120.00'), currency='USD', provider_state='failed', provider_event_id='fevt10', provider_state_at=datetime.datetime.now(tz=datetime.timezone.utc), provider_failure_code='card_declined', order_id=order.id)
    db.add(p)
    db.commit()

    rt = assess_order_revenue(db, order.id)
    res = diagnose(db, rt, order_id=order.id, payment_id=p.id, auth_stale_after=timedelta(minutes=30), abandonment_after=timedelta(days=1))
    assert 'notify_customer_failure' in res.suggested_actions
    assert 'provider_failure_code' in res.evidence or any('provider_failure_code' in cp for cp in (res.evidence.get('contributing_payments') or []))


def test_no_db_mutation_performed(db_session):
    db = db_session
    order = Order(merchant_id=1, external_id='d11', amount_total=Decimal('130.00'), currency='USD')
    db.add(order)
    db.commit()
    before_orders = db.query(Order).count()
    before_payments = db.query(Payment).count()
    rt = assess_order_revenue(db, order.id)
    _ = diagnose(db, rt, order_id=order.id, payment_id=None, auth_stale_after=timedelta(minutes=30), abandonment_after=timedelta(days=1))
    after_orders = db.query(Order).count()
    after_payments = db.query(Payment).count()
    assert before_orders == after_orders
    assert before_payments == after_payments
