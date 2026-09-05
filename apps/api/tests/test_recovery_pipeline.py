from decimal import Decimal
import datetime

from app.domain.context_builder import build_decision_context
from app.services.recovery_pipeline import process_recovery_pipeline, MockDefaultProvider
from app.db.models import Order, Payment, RecoveryCase, ExecutionRecord, RecoveryAuditEvent
from app.db.repositories.recovery import RecoveryRepository, PostgresIdempotencyStore
from app.domain.states import RecoveryStatus
from app.domain.execution import ExecutionManager, EXEC_STATUS_EXECUTED
from app.domain.policy import PolicyDecision


def test_context_builder_construction(db_session):
    db = db_session
    order = Order(merchant_id=1, external_id="ord_cb", amount_total=Decimal("100.00"), currency="USD")
    db.add(order)
    db.commit()

    payment = Payment(
        merchant_id=1,
        provider_payment_id="pay_cb",
        amount=Decimal("100.00"),
        currency="USD",
        status="failed",
        provider_state="failed",
        provider_event_id="evt_cb",
        provider_state_at=datetime.datetime.now(tz=datetime.timezone.utc),
        order_id=order.id,
    )
    db.add(payment)
    db.commit()

    ctx = build_decision_context(db, order_id=order.id, payment_id=payment.id)
    assert ctx is not None
    assert ctx.revenue_truth.order_id == order.id
    assert ctx.diagnosis.diagnosis == "PAYMENT_FAILURE"
    assert len(ctx.action_candidates) > 0
    assert len(ctx.economic_evaluations) > 0


def test_payment_failure_creates_case_and_runs_pipeline(db_session):
    db = db_session
    order = Order(merchant_id=1, external_id="ord_pipe", amount_total=Decimal("200.00"), currency="USD")
    db.add(order)
    db.commit()

    payment = Payment(
        merchant_id=1,
        provider_payment_id="pay_pipe",
        amount=Decimal("200.00"),
        currency="USD",
        status="failed",
        provider_state="failed",
        provider_event_id="evt_pipe",
        provider_state_at=datetime.datetime.now(tz=datetime.timezone.utc),
        order_id=order.id,
    )
    db.add(payment)
    db.commit()

    # Pass mock provider that simulates success
    provider = MockDefaultProvider(behavior="success", provider_reference="prov_ref_pipe")
    case = process_recovery_pipeline(db, merchant_id=1, payment_id=payment.id, order_id=order.id, provider=provider)

    assert case is not None
    assert case.merchant_id == 1
    assert case.payment_id == payment.id
    assert case.order_id == order.id
    assert case.diagnosis == "PAYMENT_FAILURE"
    assert case.execution_id is not None

    # Check audit events created
    events = db.query(RecoveryAuditEvent).filter(RecoveryAuditEvent.recovery_case_id == case.id).all()
    event_types = [e.event_type for e in events]
    assert "CASE_CREATED" in event_types
    assert "DIAGNOSIS_COMPLETED" in event_types
    assert "DECISION_MADE" in event_types


def test_no_action_persistence(db_session):
    db = db_session
    # Payment without order or expected amount leads to unknown/no_action
    payment = Payment(
        merchant_id=1,
        provider_payment_id="pay_no_action",
        amount=Decimal("0.00"),
        currency="USD",
        status="failed",
        provider_state="failed",
        provider_event_id="evt_no_action",
        provider_state_at=datetime.datetime.now(tz=datetime.timezone.utc),
        order_id=None,
    )
    db.add(payment)
    db.commit()

    case = process_recovery_pipeline(db, merchant_id=1, payment_id=payment.id)
    assert case is not None
    assert case.status in (RecoveryStatus.NO_ACTION, RecoveryStatus.ESCALATED, RecoveryStatus.VERIFYING, RecoveryStatus.ABORTED)


def test_policy_block_persistence(db_session):
    db = db_session
    order = Order(merchant_id=1, external_id="ord_blocked", amount_total=Decimal("50.00"), currency="USD")
    db.add(order)
    db.commit()

    payment = Payment(
        merchant_id=1,
        provider_payment_id="pay_blocked",
        amount=Decimal("50.00"),
        currency="USD",
        status="failed",
        provider_state="failed",
        provider_event_id="evt_blocked",
        provider_state_at=datetime.datetime.now(tz=datetime.timezone.utc),
        order_id=order.id,
    )
    db.add(payment)
    db.commit()

    # Kill switch = True will block policy evaluation
    case = process_recovery_pipeline(db, merchant_id=1, payment_id=payment.id, order_id=order.id, merchant_kill_switch=True)
    assert case is not None
    assert case.status == RecoveryStatus.ABORTED
    assert case.policy_decision is not None
    assert case.policy_decision.get("decision") == "BLOCKED"


def test_execution_idempotency_via_postgres_store(db_session):
    store = PostgresIdempotencyStore(db=db_session)
    mgr = ExecutionManager(idempotency_store=store)

    ctx = build_decision_context(db_session, order_id=None, payment_id=None)
    pd = PolicyDecision(decision="APPROVED", action="attempt_capture_retry", approved=True, reasons=["ok"], constraints={}, evaluated_at=datetime.datetime.now(tz=datetime.timezone.utc))

    r1 = mgr.execute(pd, ctx, idempotency_key="idempotent_k1", provider=MockDefaultProvider())
    r2 = mgr.execute(pd, ctx, idempotency_key="idempotent_k1", provider=MockDefaultProvider())

    assert r1.execution_id == r2.execution_id
    assert r1.status == r2.status

    # Verify execution record exists in Postgres
    rec = db_session.query(ExecutionRecord).filter(ExecutionRecord.action == "attempt_capture_retry", ExecutionRecord.idempotency_key == "idempotent_k1").first()
    assert rec is not None


def test_verification_persistence(db_session):
    repo = RecoveryRepository(db=db_session)
    case = repo.create_case(merchant_id=1, customer_id=None, order_id=None, payment_id=None, status="open", reason=None, details=None, context_version=1, recoverable_amount=None, currency=None)

    er = repo.create_execution_record(
        recovery_case_id=case.id,
        action="attempt_capture_retry",
        idempotency_key="verif_k1",
        status="EXECUTED",
        provider_reference="prov_verif_1",
        started_at=datetime.datetime.now(tz=datetime.timezone.utc),
        completed_at=datetime.datetime.now(tz=datetime.timezone.utc),
        result={},
    )

    exec_id = f"exec-{er.action}-{er.idempotency_key}"
    repo.record_verification(exec_id, "RECOVERED", {"verified": True})

    rec = repo.get_execution_record(action="attempt_capture_retry", idempotency_key="verif_k1")
    assert rec is not None
    assert rec.result is not None
    assert rec.result.get("verification_outcome") == "RECOVERED"


def test_duplicate_pipeline_call_uses_same_case(db_session):
    db = db_session
    order = Order(merchant_id=1, external_id="ord_dup_pipe", amount_total=Decimal("75.00"), currency="USD")
    db.add(order)
    db.commit()

    payment = Payment(
        merchant_id=1,
        provider_payment_id="pay_dup_pipe",
        amount=Decimal("75.00"),
        currency="USD",
        status="failed",
        provider_state="failed",
        provider_event_id="evt_dup_pipe",
        provider_state_at=datetime.datetime.now(tz=datetime.timezone.utc),
        order_id=order.id,
    )
    db.add(payment)
    db.commit()

    c1 = process_recovery_pipeline(db, merchant_id=1, payment_id=payment.id, order_id=order.id)
    c2 = process_recovery_pipeline(db, merchant_id=1, payment_id=payment.id, order_id=order.id)

    assert c1 is not None
    assert c2 is not None
    assert c1.id == c2.id


def test_two_step_recovery_verification_loop(db_session):
    db = db_session
    order = Order(merchant_id=1, external_id="ord_demo_loop", amount_total=Decimal("150.00"), currency="USD")
    db.add(order)
    db.commit()

    stale_time = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(minutes=35)
    payment = Payment(
        merchant_id=1,
        provider_payment_id="pay_demo_loop",
        amount=Decimal("150.00"),
        currency="USD",
        status="authorized",
        provider_state="authorized",
        provider_event_id="evt_auth_loop",
        provider_state_at=stale_time,
        order_id=order.id,
    )
    db.add(payment)
    db.commit()

    # Step 1: Initial pipeline run on stale authorized payment -> recommends attempt_capture_retry
    provider = MockDefaultProvider(behavior="success", provider_reference="pay_demo_loop")
    case = process_recovery_pipeline(
        db,
        merchant_id=1,
        payment_id=payment.id,
        order_id=order.id,
        trigger_reason="AUTHORIZATION_STALE",
        provider=provider,
    )

    assert case is not None
    assert case.recommended_action == "attempt_capture_retry"
    assert case.status == RecoveryStatus.VERIFYING
    initial_case_id = case.id

    # Count execution records before capture
    exec_records_before = db.query(ExecutionRecord).filter(ExecutionRecord.recovery_case_id == case.id).all()
    assert len(exec_records_before) == 1

    # Step 2: Payment state updated to captured (simulating payment.captured webhook reconciliation)
    payment.provider_state = "captured"
    payment.provider_event_id = "evt_captured_loop"
    payment.provider_state_at = datetime.datetime.now(tz=datetime.timezone.utc)
    db.add(payment)
    db.commit()

    # Step 3: Trigger pipeline re-verification for PAYMENT_CAPTURED
    updated_case = process_recovery_pipeline(
        db,
        merchant_id=1,
        payment_id=payment.id,
        order_id=order.id,
        trigger_reason="PAYMENT_CAPTURED",
        provider=provider,
    )

    assert updated_case is not None
    assert updated_case.id == initial_case_id
    assert updated_case.status == RecoveryStatus.RECOVERED
    assert updated_case.verification_outcome == "RECOVERED"

    # Verify no duplicate execution record was created
    exec_records_after = db.query(ExecutionRecord).filter(ExecutionRecord.recovery_case_id == case.id).all()
    assert len(exec_records_after) == 1

    # Step 4: Duplicate PAYMENT_CAPTURED call returns existing RECOVERED case without re-processing
    dup_case = process_recovery_pipeline(
        db,
        merchant_id=1,
        payment_id=payment.id,
        order_id=order.id,
        trigger_reason="PAYMENT_CAPTURED",
        provider=provider,
    )
    assert dup_case is None or dup_case.status == RecoveryStatus.RECOVERED
