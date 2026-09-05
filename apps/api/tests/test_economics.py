from decimal import Decimal
import datetime

from app.domain.economics import evaluate, evaluate_batch, EconomicEvaluation
from app.domain.actions import ActionCandidate
from app.domain.probability import ProbabilityEstimate
from app.domain.revenue_truth import RevenueTruthResult


def make_revenue_truth(recoverable_amount=None, currency="USD"):
    return RevenueTruthResult(
        order_id=1,
        expected_amount=Decimal("100"),
        captured_amount=Decimal("50"),
        currency=currency,
        recoverable_amount=recoverable_amount,
        resolution="ok",
        contributing_payments=[],
    )


def make_candidate(action, eligible=True, reason="test"):
    return ActionCandidate(action=action, eligible=eligible, reason=reason, constraints={})


def make_prob(action, prob: Decimal, confidence="high"):
    return ProbabilityEstimate(action=action, probability=prob, confidence=confidence, evidence={}, model_version="deterministic-v1")


def test_recoverable_zero():
    rt = make_revenue_truth(recoverable_amount=Decimal("0"))
    c = make_candidate("attempt_capture_retry", eligible=True)
    p = make_prob(c.action, Decimal("0.5"))
    costs = {c.action: Decimal("5.00")}
    ev = evaluate(c, p, rt, costs)
    assert ev.recoverable_amount == Decimal("0")
    assert ev.expected_recovered_amount == Decimal("0.00")
    assert ev.expected_net_recovery == Decimal("-5.00")
    assert ev.economically_viable is False


def test_recoverable_none():
    rt = make_revenue_truth(recoverable_amount=None)
    c = make_candidate("notify_customer_failure", eligible=True)
    p = make_prob(c.action, Decimal("0.6"))
    costs = {c.action: Decimal("1.00")}
    ev = evaluate(c, p, rt, costs)
    assert ev.recoverable_amount is None
    assert ev.expected_recovered_amount is None
    assert ev.expected_net_recovery is None
    assert ev.economically_viable is False


def test_probability_zero_and_one():
    rt = make_revenue_truth(recoverable_amount=Decimal("20"))
    c0 = make_candidate("a0", eligible=True)
    p0 = make_prob(c0.action, Decimal("0"))
    costs0 = {c0.action: Decimal("0.00")}
    ev0 = evaluate(c0, p0, rt, costs0)
    assert ev0.expected_recovered_amount == Decimal("0.00")

    c1 = make_candidate("a1", eligible=True)
    p1 = make_prob(c1.action, Decimal("1"))
    costs1 = {c1.action: Decimal("5.00")}
    ev1 = evaluate(c1, p1, rt, costs1)
    assert ev1.expected_recovered_amount == Decimal("20.00")


def test_intervention_cost_zero_and_greater():
    rt = make_revenue_truth(recoverable_amount=Decimal("10"))
    c = make_candidate("act", eligible=True)
    p = make_prob(c.action, Decimal("0.5"))
    costs_zero = {c.action: Decimal("0.00")}
    evz = evaluate(c, p, rt, costs_zero)
    assert evz.expected_recovered_amount == Decimal("5.00")
    assert evz.expected_net_recovery == Decimal("5.00")

    costs_high = {c.action: Decimal("6.00")}
    evh = evaluate(c, p, rt, costs_high)
    assert evh.expected_recovered_amount == Decimal("5.00")
    assert evh.expected_net_recovery == Decimal("-1.00")
    assert evh.economically_viable is False


def test_unknown_currency():
    rt = make_revenue_truth(recoverable_amount=Decimal("10"), currency=None)
    c = make_candidate("act", eligible=True)
    p = make_prob(c.action, Decimal("0.5"))
    costs = {c.action: Decimal("1.00")}
    ev = evaluate(c, p, rt, costs)
    assert ev.currency is None
    assert ev.economically_viable is False


def test_ineligible_action():
    rt = make_revenue_truth(recoverable_amount=Decimal("10"))
    c = make_candidate("act", eligible=False)
    p = make_prob(c.action, Decimal("0.8"))
    costs = {c.action: Decimal("1.00")}
    ev = evaluate(c, p, rt, costs)
    assert ev.eligible is False
    assert ev.expected_recovered_amount is None
    assert ev.expected_net_recovery is None


def test_multiple_actions_independent():
    rt = make_revenue_truth(recoverable_amount=Decimal("100"))
    c1 = make_candidate("a1", eligible=True)
    c2 = make_candidate("a2", eligible=True)
    p1 = make_prob(c1.action, Decimal("0.1"))
    p2 = make_prob(c2.action, Decimal("0.9"))
    costs = {"a1": Decimal("1.00"), "a2": Decimal("10.00")}
    ev1 = evaluate(c1, p1, rt, costs)
    ev2 = evaluate(c2, p2, rt, costs)
    assert ev1.expected_recovered_amount == Decimal("10.00")
    assert ev2.expected_recovered_amount == Decimal("90.00")
    assert ev1.expected_net_recovery == Decimal("9.00")
    assert ev2.expected_net_recovery == Decimal("80.00")


def test_deterministic_and_decimal_arithmetic():
    rt = make_revenue_truth(recoverable_amount=Decimal("33.33"))
    c = make_candidate("act", eligible=True)
    p = make_prob(c.action, Decimal("0.3333"))
    costs = {c.action: Decimal("0.00")}
    ev1 = evaluate(c, p, rt, costs)
    ev2 = evaluate(c, p, rt, costs)
    assert ev1.expected_recovered_amount == ev2.expected_recovered_amount
    assert isinstance(ev1.expected_recovered_amount, Decimal)


def test_batch_evaluate_requires_probabilities():
    rt = make_revenue_truth(recoverable_amount=Decimal("10"))
    c1 = make_candidate("a1", eligible=True)
    c2 = make_candidate("a2", eligible=True)
    pmap = {"a1": make_prob("a1", Decimal("0.5"))}
    costs = {"a1": Decimal("1.00"), "a2": Decimal("1.00")}
    try:
        _ = evaluate_batch([c1, c2], pmap, rt, costs)
        assert False, "Expected KeyError for missing probability"
    except KeyError:
        pass


def test_positive_expected_net_recovery_is_economically_viable():
    """Invariant: Any eligible candidate action with expected_net_recovery > 0 MUST be marked economically_viable = True."""
    rt = make_revenue_truth(recoverable_amount=Decimal("100.00"))
    c = make_candidate("notify_customer_failure", eligible=True)
    p = make_prob(c.action, Decimal("0.60"))
    costs = {c.action: Decimal("10.00")}
    ev = evaluate(c, p, rt, costs)
    assert ev.expected_net_recovery == Decimal("50.00")
    assert ev.economically_viable is True
    assert ev.reason == "Expected net recovery positive"

