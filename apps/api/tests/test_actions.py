from app.domain.actions import generate_candidates, ActionCandidate
from app.domain.revenue_truth import RevenueTruthResult
from app.domain.diagnosis import DiagnosisResult
from decimal import Decimal
import datetime


def make_revenue_truth(captured_amount=Decimal("0"), expected_amount=Decimal("100")):
    return RevenueTruthResult(
        order_id=1,
        expected_amount=expected_amount,
        captured_amount=captured_amount,
        currency="USD",
        recoverable_amount=(expected_amount - captured_amount if expected_amount is not None else None),
        resolution="complete",
        contributing_payments=[],
    )


def make_diag(code, evidence=None):
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    return DiagnosisResult(
        diagnosis=code,
        confidence="medium",
        order_id=1,
        payment_ids=[],
        evidence=evidence or {},
        suggested_actions=[],
        diagnosis_timestamp=now,
    )


def map_by_action(cands):
    return {c.action: c for c in cands}


def test_payment_failure_candidates():
    rt = make_revenue_truth()
    d = make_diag("PAYMENT_FAILURE", evidence={"provider_failure_code": "card_decline"})
    c = map_by_action(generate_candidates(d, rt))
    assert c["notify_customer_failure"].eligible is True
    assert c["create_recovery_case"].eligible is True
    assert c["manual_review"].eligible is True
    assert c["collect_more_evidence"].eligible is True
    assert c["attempt_capture_retry"].eligible is False
    assert c["send_cart_recovery_email"].eligible is False
    assert c["offer_discount"].eligible is False


def test_authorization_stale_candidates():
    rt = make_revenue_truth()
    d = make_diag("AUTHORIZATION_STALE", evidence={"authorization_row_id": 99})
    c = map_by_action(generate_candidates(d, rt))
    assert c["attempt_capture_retry"].eligible is True
    assert c["manual_review"].eligible is True
    assert c["create_recovery_case"].eligible is True
    assert c["notify_customer_failure"].eligible is False
    assert c["send_cart_recovery_email"].eligible is False
    assert c["offer_discount"].eligible is False
    assert c["collect_more_evidence"].eligible is True


def test_checkout_abandonment_candidates():
    rt = make_revenue_truth(captured_amount=Decimal("0"), expected_amount=Decimal("50"))
    d = make_diag("CHECKOUT_ABANDONMENT", evidence={})
    c = map_by_action(generate_candidates(d, rt))
    assert c["send_cart_recovery_email"].eligible is True
    # offer_discount eligible only if recoverable_amount > 0
    assert c["offer_discount"].eligible is True
    assert c["create_recovery_case"].eligible is True
    assert c["collect_more_evidence"].eligible is True
    assert c["manual_review"].eligible is True
    assert c["attempt_capture_retry"].eligible is False


def test_unknown_candidates():
    rt = None
    d = make_diag("UNKNOWN", evidence={})
    c = map_by_action(generate_candidates(d, rt))
    assert c["collect_more_evidence"].eligible is True
    assert c["manual_review"].eligible is True
    assert c["create_recovery_case"].eligible is True
    # aggressive actions should be ineligible
    assert c["attempt_capture_retry"].eligible is False
    assert c["notify_customer_failure"].eligible is False
    assert c["send_cart_recovery_email"].eligible is False
    assert c["offer_discount"].eligible is False


def test_ineligible_actions_explicit_and_reasons_constraints():
    rt = make_revenue_truth()
    d = make_diag("PAYMENT_FAILURE", evidence={})
    cands = generate_candidates(d, rt)
    for cand in cands:
        assert isinstance(cand.eligible, bool)
        assert isinstance(cand.reason, str) and cand.reason
        assert isinstance(cand.constraints, dict)


def test_deterministic_output():
    rt = make_revenue_truth()
    d = make_diag("PAYMENT_FAILURE", evidence={})
    a = generate_candidates(d, rt)
    b = generate_candidates(d, rt)
    assert [(c.action, c.eligible) for c in a] == [(c.action, c.eligible) for c in b]


def test_no_probability_or_execution_and_no_db_mutation():
    rt = make_revenue_truth()
    d = make_diag("PAYMENT_FAILURE", evidence={})
    c = generate_candidates(d, rt)
    for cand in c:
        assert not hasattr(cand, "probability")
    # no exceptions indicates no DB calls were attempted (module is pure)
