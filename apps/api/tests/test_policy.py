from datetime import datetime, timezone
from decimal import Decimal

from app.domain.policy import PolicyContext, evaluate_policy, PolicyDecision
from app.domain.decision import DecisionContext, DecisionResult
from app.domain.revenue_truth import RevenueTruthResult
from app.domain.diagnosis import DiagnosisResult
from app.domain.actions import ActionCandidate
from app.domain.economics import EconomicEvaluation


def make_rt(recoverable=None, currency="USD"):
    return RevenueTruthResult(
        order_id=1,
        expected_amount=Decimal("100"),
        captured_amount=Decimal("0"),
        currency=currency,
        recoverable_amount=recoverable,
        resolution="ok",
        contributing_payments=[],
    )


def make_diag():
    return DiagnosisResult(
        diagnosis="PAYMENT_FAILURE",
        confidence="high",
        order_id=1,
        payment_ids=[],
        evidence={},
        suggested_actions=[],
        diagnosis_timestamp=datetime.now(tz=timezone.utc),
    )


def make_candidate(action, eligible=True):
    return ActionCandidate(action=action, eligible=eligible, reason="r", constraints={})


def make_econ(action, eligible, net, viable=True):
    return EconomicEvaluation(
        action=action,
        eligible=eligible,
        recoverable_amount=Decimal("50") if net is not None else None,
        success_probability=Decimal("0.5"),
        expected_recovered_amount=Decimal("25.00") if net is not None else None,
        intervention_cost=Decimal("1.00"),
        expected_net_recovery=(Decimal(net) if net is not None else None),
        currency="USD",
        economically_viable=viable,
        reason="",
        evidence={},
    )


def make_context_and_result(ctx_version=1, recommend_action=None):
    rt = make_rt(recoverable=Decimal("50"))
    diag = make_diag()
    ctx = DecisionContext(
        context_version=ctx_version,
        generated_at=datetime.now(tz=timezone.utc),
        revenue_truth=rt,
        diagnosis=diag,
        action_candidates=[make_candidate("a", eligible=True)],
        economic_evaluations=[make_econ("a", True, "10")],
    )
    if recommend_action:
        dr = DecisionResult(
            decision="RECOMMEND_ACTION",
            recommended_action=recommend_action,
            context_version=ctx_version,
            decided_at=datetime.now(tz=timezone.utc),
            rationale="",
            evidence={},
            agent_version="det",
            confidence="high",
        )
    else:
        dr = DecisionResult(
            decision="NO_ACTION",
            recommended_action=None,
            context_version=ctx_version,
            decided_at=datetime.now(tz=timezone.utc),
            rationale="",
            evidence={},
            agent_version="det",
            confidence="high",
        )
    return ctx, dr


def test_no_action_remains_no_action():
    ctx, dr = make_context_and_result()
    pc = PolicyContext(decision_context=ctx, decision_result=dr, mode="AUTONOMOUS", remaining_budget=Decimal("100"))
    pd = evaluate_policy(pc)
    assert pd.decision == "NO_ACTION"


def test_needs_review_remains_needs_review():
    # construct NEEDS_REVIEW
    ctx, _ = make_context_and_result()
    dr = DecisionResult(
        decision="NEEDS_REVIEW",
        recommended_action=None,
        context_version=1,
        decided_at=datetime.now(tz=timezone.utc),
        rationale="",
        evidence={},
        agent_version="det",
        confidence="low",
    )
    pc = PolicyContext(decision_context=ctx, decision_result=dr, mode="AUTONOMOUS", remaining_budget=Decimal("100"))
    pd = evaluate_policy(pc)
    assert pd.decision == "NEEDS_REVIEW"


def test_valid_recommend_autonomous_approved():
    ctx, _ = make_context_and_result(recommend_action="a")
    dr = DecisionResult(
        decision="RECOMMEND_ACTION",
        recommended_action="a",
        context_version=1,
        decided_at=datetime.now(tz=timezone.utc),
        rationale="",
        evidence={},
        agent_version="det",
        confidence="high",
    )
    pc = PolicyContext(decision_context=ctx, decision_result=dr, mode="AUTONOMOUS", remaining_budget=Decimal("100"))
    pd = evaluate_policy(pc)
    assert pd.decision == "APPROVED" and pd.approved is True


def test_observe_blocks_autonomous():
    ctx, _ = make_context_and_result(recommend_action="a")
    dr = DecisionResult(
        decision="RECOMMEND_ACTION",
        recommended_action="a",
        context_version=1,
        decided_at=datetime.now(tz=timezone.utc),
        rationale="",
        evidence={},
        agent_version="det",
        confidence="high",
    )
    pc = PolicyContext(decision_context=ctx, decision_result=dr, mode="OBSERVE", remaining_budget=Decimal("100"))
    pd = evaluate_policy(pc)
    assert pd.decision == "BLOCKED" and "mode_observe" in pd.reasons


def test_recommend_mode_blocks_autonomous():
    ctx, _ = make_context_and_result(recommend_action="a")
    dr = DecisionResult(
        decision="RECOMMEND_ACTION",
        recommended_action="a",
        context_version=1,
        decided_at=datetime.now(tz=timezone.utc),
        rationale="",
        evidence={},
        agent_version="det",
        confidence="high",
    )
    pc = PolicyContext(decision_context=ctx, decision_result=dr, mode="RECOMMEND", remaining_budget=Decimal("100"))
    pd = evaluate_policy(pc)
    assert pd.decision == "BLOCKED" and "mode_recommend" in pd.reasons


def test_kill_switch_blocks_action():
    ctx, _ = make_context_and_result(recommend_action="a")
    dr = DecisionResult(
        decision="RECOMMEND_ACTION",
        recommended_action="a",
        context_version=1,
        decided_at=datetime.now(tz=timezone.utc),
        rationale="",
        evidence={},
        agent_version="det",
        confidence="high",
    )
    pc = PolicyContext(decision_context=ctx, decision_result=dr, mode="AUTONOMOUS", remaining_budget=Decimal("100"), merchant_kill_switch=True)
    pd = evaluate_policy(pc)
    assert pd.decision == "BLOCKED" and "merchant_kill_switch_enabled" in pd.reasons


def test_recovery_budget_sufficient_allowed():
    ctx, _ = make_context_and_result(recommend_action=None)
    # use a financial action so recovery budget check applies
    ctx.action_candidates.append(make_candidate("attempt_capture_retry", eligible=True))
    ctx.economic_evaluations.append(make_econ("attempt_capture_retry", True, "10"))
    dr = DecisionResult(
        decision="RECOMMEND_ACTION",
        recommended_action="attempt_capture_retry",
        context_version=1,
        decided_at=datetime.now(tz=timezone.utc),
        rationale="",
        evidence={},
        agent_version="det",
        confidence="high",
    )
    pc = PolicyContext(decision_context=ctx, decision_result=dr, mode="AUTONOMOUS", remaining_budget=Decimal("100"))
    pd = evaluate_policy(pc)
    assert pd.decision == "APPROVED"


def test_recovery_budget_insufficient_blocked():
    ctx, _ = make_context_and_result(recommend_action=None)
    # make recoverable larger than budget
    ctx.revenue_truth.recoverable_amount = Decimal("200")
    # use a financial action so recovery budget check applies
    ctx.action_candidates.append(make_candidate("attempt_capture_retry", eligible=True))
    ctx.economic_evaluations.append(make_econ("attempt_capture_retry", True, "10"))
    dr = DecisionResult(
        decision="RECOMMEND_ACTION",
        recommended_action="attempt_capture_retry",
        context_version=1,
        decided_at=datetime.now(tz=timezone.utc),
        rationale="",
        evidence={},
        agent_version="det",
        confidence="high",
    )
    pc = PolicyContext(decision_context=ctx, decision_result=dr, mode="AUTONOMOUS", remaining_budget=Decimal("100"))
    pd = evaluate_policy(pc)
    assert pd.decision == "BLOCKED" and "insufficient_budget" in pd.reasons


def test_unknown_recoverable_fails_closed_for_financial_action():
    ctx, _ = make_context_and_result(recommend_action="a")
    ctx.revenue_truth.recoverable_amount = None
    dr = DecisionResult(
        decision="RECOMMEND_ACTION",
        recommended_action="attempt_capture_retry",
        context_version=1,
        decided_at=datetime.now(tz=timezone.utc),
        rationale="",
        evidence={},
        agent_version="det",
        confidence="high",
    )
    # ensure candidate exists
    ctx.action_candidates.append(make_candidate("attempt_capture_retry", eligible=True))
    pc = PolicyContext(decision_context=ctx, decision_result=dr, mode="AUTONOMOUS", remaining_budget=Decimal("100"))
    pd = evaluate_policy(pc)
    assert pd.decision == "BLOCKED" and "unknown_recoverable_amount" in pd.reasons


def test_contact_fatigue_blocks_contact_actions():
    ctx, _ = make_context_and_result(recommend_action="a")
    # set action to contact action
    dr = DecisionResult(
        decision="RECOMMEND_ACTION",
        recommended_action="notify_customer_failure",
        context_version=1,
        decided_at=datetime.now(tz=timezone.utc),
        rationale="",
        evidence={},
        agent_version="det",
        confidence="high",
    )
    ctx.action_candidates.append(make_candidate("notify_customer_failure", eligible=True))
    pc = PolicyContext(decision_context=ctx, decision_result=dr, mode="AUTONOMOUS", remaining_budget=Decimal("100"), contact_count=3, max_contacts=3)
    pd = evaluate_policy(pc)
    assert pd.decision == "BLOCKED" and "contact_fatigue" in pd.reasons


def test_non_contact_action_unaffected_by_contact_fatigue():
    ctx, _ = make_context_and_result(recommend_action="a")
    dr = DecisionResult(
        decision="RECOMMEND_ACTION",
        recommended_action="manual_review",
        context_version=1,
        decided_at=datetime.now(tz=timezone.utc),
        rationale="",
        evidence={},
        agent_version="det",
        confidence="high",
    )
    ctx.action_candidates.append(make_candidate("manual_review", eligible=True))
    pc = PolicyContext(decision_context=ctx, decision_result=dr, mode="AUTONOMOUS", remaining_budget=Decimal("100"), contact_count=10, max_contacts=3)
    pd = evaluate_policy(pc)
    # manual_review should not be blocked by contact fatigue
    assert pd.decision == "APPROVED"


def test_ineligible_candidate_blocked_and_missing_candidate_blocked():
    ctx, _ = make_context_and_result(recommend_action="a")
    # recommend b which is missing
    dr_missing = DecisionResult(
        decision="RECOMMEND_ACTION",
        recommended_action="b",
        context_version=1,
        decided_at=datetime.now(tz=timezone.utc),
        rationale="",
        evidence={},
        agent_version="det",
        confidence="high",
    )
    pc = PolicyContext(decision_context=ctx, decision_result=dr_missing, mode="AUTONOMOUS", remaining_budget=Decimal("100"))
    pd = evaluate_policy(pc)
    assert pd.decision == "BLOCKED" and "missing_candidate" in pd.reasons

    # recommend a but mark candidate ineligible
    ctx.action_candidates[0].eligible = False
    dr_ineligible = DecisionResult(
        decision="RECOMMEND_ACTION",
        recommended_action="a",
        context_version=1,
        decided_at=datetime.now(tz=timezone.utc),
        rationale="",
        evidence={},
        agent_version="det",
        confidence="high",
    )
    pc2 = PolicyContext(decision_context=ctx, decision_result=dr_ineligible, mode="AUTONOMOUS", remaining_budget=Decimal("100"))
    pd2 = evaluate_policy(pc2)
    assert pd2.decision == "BLOCKED" and "candidate_ineligible" in pd2.reasons


def test_stale_context_blocks():
    ctx, _ = make_context_and_result(recommend_action="a")
    dr = DecisionResult(
        decision="RECOMMEND_ACTION",
        recommended_action="a",
        context_version=999,
        decided_at=datetime.now(tz=timezone.utc),
        rationale="",
        evidence={},
        agent_version="det",
        confidence="high",
    )
    pc = PolicyContext(decision_context=ctx, decision_result=dr, mode="AUTONOMOUS", remaining_budget=Decimal("100"))
    pd = evaluate_policy(pc)
    assert pd.decision == "BLOCKED" and "stale_context" in pd.reasons


def test_deterministic_and_decimal_and_timestamp():
    ctx, _ = make_context_and_result(recommend_action="a")
    dr = DecisionResult(
        decision="RECOMMEND_ACTION",
        recommended_action="a",
        context_version=1,
        decided_at=datetime.now(tz=timezone.utc),
        rationale="",
        evidence={},
        agent_version="det",
        confidence="high",
    )
    pc = PolicyContext(decision_context=ctx, decision_result=dr, mode="AUTONOMOUS", remaining_budget=Decimal("100"))
    pd1 = evaluate_policy(pc)
    pd2 = evaluate_policy(pc)
    assert pd1.decision == pd2.decision
    assert isinstance(pd1.evaluated_at.tzinfo, type(datetime.now(tz=timezone.utc).tzinfo))
