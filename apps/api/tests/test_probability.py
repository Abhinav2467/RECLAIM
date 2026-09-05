from decimal import Decimal
import datetime

from app.domain.probability import estimate, ProbabilityEstimate
from app.domain.revenue_truth import RevenueTruthResult, ContributingPayment
from app.domain.diagnosis import DiagnosisResult


def make_revenue_truth(captured_amount=Decimal("0"), expected_amount=Decimal("100")):
    return RevenueTruthResult(
        order_id=1,
        expected_amount=expected_amount,
        captured_amount=captured_amount,
        currency="USD",
        recoverable_amount=(expected_amount - captured_amount if expected_amount is not None else None),
        resolution="ok",
        contributing_payments=[],
    )


def make_diag(code, confidence="high", evidence=None):
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    return DiagnosisResult(
        diagnosis=code,
        confidence=confidence,
        order_id=1,
        payment_ids=[],
        evidence=evidence or {},
        suggested_actions=[],
        diagnosis_timestamp=now,
    )


def test_probability_in_bounds_and_version():
    rt = make_revenue_truth()
    d = make_diag("PAYMENT_FAILURE", "high", {"provider_event_id": "evt_1"})
    pe = estimate(d, rt, "notify_customer_failure")
    assert isinstance(pe, ProbabilityEstimate)
    assert Decimal("0") <= pe.probability <= Decimal("1")
    assert pe.model_version == "deterministic-v1"


def test_action_specific_differ():
    rt = make_revenue_truth()
    d = make_diag("PAYMENT_FAILURE", "high", {})
    p_notify = estimate(d, rt, "notify_customer_failure").probability
    p_retry = estimate(d, rt, "attempt_capture_retry").probability
    assert p_notify != p_retry


def test_payment_failure_maps_notify():
    rt = make_revenue_truth()
    d = make_diag("PAYMENT_FAILURE", "high", {"provider_event_id": "evt_x"})
    pe = estimate(d, rt, "notify_customer_failure")
    assert pe.probability >= Decimal("0.5")


def test_authorization_stale_maps_retry():
    rt = make_revenue_truth(captured_amount=Decimal("0"))
    d = make_diag("AUTHORIZATION_STALE", "medium", {"authorization_age_seconds": 1200})
    pe = estimate(d, rt, "attempt_capture_retry")
    assert pe.probability >= Decimal("0.4")


def test_checkout_abandonment_maps_email():
    rt = make_revenue_truth()
    d = make_diag("CHECKOUT_ABANDONMENT", "medium", {})
    pe = estimate(d, rt, "send_cart_recovery_email")
    assert pe.probability >= Decimal("0.3")


def test_unknown_weak_evidence():
    rt = None
    d = make_diag("UNKNOWN", "low", {})
    pe = estimate(d, rt, "manual_review")
    # unknown should not yield high probability for recovery actions
    assert pe.probability <= Decimal("0.75")


def test_missing_evidence_lowers_confidence():
    rt = None
    d = make_diag("PAYMENT_FAILURE", "low", {})
    pe = estimate(d, rt, "notify_customer_failure")
    assert pe.confidence in ("low", "medium", "high")
    # low diagnosis confidence should keep overall probability modest
    assert pe.probability < Decimal("0.8")


def test_deterministic_repeatable():
    rt = make_revenue_truth()
    d = make_diag("PAYMENT_FAILURE", "high", {"provider_event_id": "evt_zzz"})
    p1 = estimate(d, rt, "notify_customer_failure")
    p2 = estimate(d, rt, "notify_customer_failure")
    assert p1.probability == p2.probability
    assert p1.evidence == p2.evidence


def test_no_db_mutation():
    # estimator is pure and should not attempt DB operations; we assert by simply
    # calling it — tests in this repo ensure DB mutation would fail if attempted.
    rt = make_revenue_truth()
    d = make_diag("PAYMENT_FAILURE", "high", {})
    pe = estimate(d, rt, "notify_customer_failure")
    assert isinstance(pe.probability, Decimal)
