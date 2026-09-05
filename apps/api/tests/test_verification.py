from datetime import datetime, timezone
from decimal import Decimal

from app.domain.execution import ExecutionResult
from app.domain.verification import verify_execution, VERIF_STATUS_RECOVERED, VERIF_STATUS_PENDING, VERIF_STATUS_NOT_RECOVERED, VERIF_STATUS_FAILED
from app.domain.revenue_truth import RevenueTruthResult, ContributingPayment
from app.domain.decision import DecisionContext


def make_execution(action: str, status: str, provider_reference: str | None):
    return ExecutionResult(
        action=action,
        status=status,
        execution_id=f"e-{action}-1",
        started_at=datetime.now(tz=timezone.utc),
        completed_at=None if status == "PENDING" else datetime.now(tz=timezone.utc),
        provider_reference=provider_reference,
        message="",
        evidence={},
    )


def make_context_with_payment(provider_payment_id: str | None, state: str):
    cp = ContributingPayment(payment_id=1, provider_payment_id=provider_payment_id, amount=Decimal("100"), currency="USD", provider_state=state, provider_event_id=None, provider_state_at=datetime.now(tz=timezone.utc))
    rt = RevenueTruthResult(order_id=1, expected_amount=Decimal("100"), captured_amount=(Decimal("100") if state == "captured" else Decimal("0")), currency="USD", recoverable_amount=(Decimal("0") if state == "captured" else Decimal("100")), resolution="complete", contributing_payments=[cp])
    ctx = DecisionContext(context_version=1, generated_at=datetime.now(tz=timezone.utc), revenue_truth=rt, diagnosis=None, action_candidates=[], economic_evaluations=[])
    return ctx


def test_successful_execution_but_unverified_financial_state_is_pending():
    ex = make_execution("attempt_capture_retry", "EXECUTED", "prov-1")
    ctx = make_context_with_payment(provider_payment_id=None, state="failed")
    vr = verify_execution(ex, ctx)
    assert vr.status == VERIF_STATUS_PENDING


def test_confirmed_capture_returns_recovered():
    ex = make_execution("attempt_capture_retry", "EXECUTED", "prov-42")
    ctx = make_context_with_payment(provider_payment_id="prov-42", state="captured")
    vr = verify_execution(ex, ctx)
    assert vr.status == VERIF_STATUS_RECOVERED and vr.verified is True


def test_failed_execution_reports_failed():
    ex = make_execution("attempt_capture_retry", "FAILED", None)
    ctx = make_context_with_payment(provider_payment_id=None, state="failed")
    vr = verify_execution(ex, ctx)
    assert vr.status == VERIF_STATUS_FAILED


def test_provider_pending_reports_pending():
    ex = make_execution("attempt_capture_retry", "PENDING", "prov-p")
    ctx = make_context_with_payment(provider_payment_id=None, state="failed")
    vr = verify_execution(ex, ctx)
    assert vr.status == VERIF_STATUS_PENDING


def test_notification_execution_not_recovered():
    ex = make_execution("notify_customer_failure", "EXECUTED", "msg-1")
    ctx = make_context_with_payment(provider_payment_id=None, state="failed")
    vr = verify_execution(ex, ctx)
    assert vr.status == VERIF_STATUS_NOT_RECOVERED and vr.verified is True


def test_verification_preserves_provider_reference_and_timestamps():
    ex = make_execution("attempt_capture_retry", "EXECUTED", "prov-7")
    ctx = make_context_with_payment(provider_payment_id="prov-7", state="captured")
    vr = verify_execution(ex, ctx)
    assert vr.provider_reference == "prov-7"
    assert vr.verified_at.tzinfo is not None
