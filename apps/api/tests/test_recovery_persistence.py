from datetime import datetime, timezone
from decimal import Decimal
import threading

from app.db.repositories.recovery import RecoveryRepository
from app.db.models import Merchant, Customer, Order, Payment, RecoveryCase, ExecutionRecord, RecoveryAuditEvent
from app.db.session import SessionLocal


def test_create_case_and_append_event(db_session):
    repo = RecoveryRepository(db=db_session)
    rc = repo.create_case(merchant_id=1, customer_id=None, order_id=None, payment_id=None, status="open", reason="test", details={"foo":"bar"}, context_version=1, recoverable_amount=Decimal("10.00"), currency="USD")
    assert isinstance(rc, RecoveryCase)

    ev = repo.append_event(recovery_case_id=rc.id, event_type="CASE_CREATED", actor="system", action="create", status="open", idempotency_key=None, evidence={"init": True}, message="created")
    assert isinstance(ev, RecoveryAuditEvent)


def test_execution_idempotency(db_session):
    repo = RecoveryRepository(db=db_session)
    rc = repo.create_case(merchant_id=1, customer_id=None, order_id=None, payment_id=None, status="open", reason=None, details=None, context_version=1, recoverable_amount=None, currency=None)

    now = datetime.now(timezone.utc)
    er1 = repo.create_execution_record(recovery_case_id=rc.id, action="attempt_capture_retry", idempotency_key="k1", status="PENDING", provider_reference=None, started_at=now, completed_at=None, result={})
    er2 = repo.create_execution_record(recovery_case_id=rc.id, action="attempt_capture_retry", idempotency_key="k1", status="PENDING", provider_reference=None, started_at=now, completed_at=None, result={})
    assert er1.id == er2.id


def test_execution_unique_different_keys(db_session):
    repo = RecoveryRepository(db=db_session)
    rc = repo.create_case(merchant_id=1, customer_id=None, order_id=None, payment_id=None, status="open", reason=None, details=None, context_version=1, recoverable_amount=None, currency=None)
    now = datetime.now(timezone.utc)
    er1 = repo.create_execution_record(recovery_case_id=rc.id, action="attempt_capture_retry", idempotency_key="k-a", status="PENDING", provider_reference=None, started_at=now, completed_at=None, result={})
    er2 = repo.create_execution_record(recovery_case_id=rc.id, action="attempt_capture_retry", idempotency_key="k-b", status="PENDING", provider_reference=None, started_at=now, completed_at=None, result={})
    assert er1.id != er2.id


def test_optimistic_concurrency(db_session):
    repo = RecoveryRepository(db=db_session)
    rc = repo.create_case(merchant_id=1, customer_id=None, order_id=None, payment_id=None, status="open", reason=None, details=None, context_version=1, recoverable_amount=None, currency=None)
    # update with correct version
    updated = repo.update_case_with_version(case_id=rc.id, expected_version=1, updates={"status": "in_progress"})
    assert updated is not None and updated.version == 2
    # stale update should be rejected
    stale = repo.update_case_with_version(case_id=rc.id, expected_version=1, updates={"status": "closed"})
    assert stale is None


def test_active_recovery_case_uniqueness_and_convergence(db_session):
    repo = RecoveryRepository(db=db_session)

    m = db_session.get(Merchant, 1)
    if not m:
        m = Merchant(id=1, name="Test Merchant")
        db_session.add(m)
        db_session.commit()

    order = Order(merchant_id=1, external_id="ord_uniq_test", amount_total=Decimal("100.00"), currency="USD")
    db_session.add(order)
    db_session.commit()

    payment = Payment(merchant_id=1, order_id=order.id, provider_payment_id="pay_uniq_test", amount=Decimal("100.00"), currency="USD", status="failed", provider_state="failed")
    db_session.add(payment)
    db_session.commit()

    # 1. Create first active case for payment
    rc1 = repo.create_case(
        merchant_id=1, customer_id=None, order_id=order.id, payment_id=payment.id,
        status="DETECTED", reason="PAYMENT_FAILURE", details={}, context_version=1,
        recoverable_amount=Decimal("100.00"), currency="USD"
    )
    assert rc1.id is not None

    # 2. Duplicate active case creation attempt for same payment_id converges on existing active case
    rc2 = repo.create_case(
        merchant_id=1, customer_id=None, order_id=order.id, payment_id=payment.id,
        status="DETECTED", reason="PAYMENT_FAILURE", details={}, context_version=1,
        recoverable_amount=Decimal("100.00"), currency="USD"
    )
    assert rc2.id == rc1.id

    # 3. Transition rc1 to terminal state (RECOVERED)
    repo.update_case_with_version(rc1.id, expected_version=1, updates={"status": "RECOVERED"})

    # 4. Creating a new active case for payment after terminal state succeeds
    rc3 = repo.create_case(
        merchant_id=1, customer_id=None, order_id=order.id, payment_id=payment.id,
        status="DETECTED", reason="PAYMENT_FAILURE", details={}, context_version=1,
        recoverable_amount=Decimal("100.00"), currency="USD"
    )
    assert rc3.id != rc1.id
