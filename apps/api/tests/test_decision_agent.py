from datetime import datetime, timezone
from decimal import Decimal

from app.agents.decision_agent import run_decision_agent, AGENT_VERSION
from app.domain.decision import DecisionContext, DecisionResult, DecisionValidationError, validate_decision_context
from app.domain.revenue_truth import RevenueTruthResult
from app.domain.diagnosis import DiagnosisResult
from app.domain.actions import ActionCandidate
from app.domain.economics import EconomicEvaluation


def make_rt(recoverable=Decimal("100"), currency="USD"):
    return RevenueTruthResult(
        order_id=1,
        expected_amount=Decimal("200"),
        captured_amount=Decimal("100"),
        currency=currency,
        recoverable_amount=recoverable,
        resolution="ok",
        contributing_payments=[],
    )


def make_diag(conf="high"):
    return DiagnosisResult(
        diagnosis="PAYMENT_FAILURE",
        confidence=conf,
        order_id=1,
        payment_ids=[],
        evidence={},
        suggested_actions=[],
        diagnosis_timestamp=datetime.now(tz=timezone.utc),
    )


def econ(action, eligible, net, currency="USD", prob_conf="high"):
    expected_net = Decimal(net) if net is not None else None
    return EconomicEvaluation(
        action=action,
        eligible=eligible,
        recoverable_amount=Decimal("100"),
        success_probability=Decimal("0.5"),
        expected_recovered_amount=Decimal("50.00"),
        intervention_cost=Decimal("1.00"),
        expected_net_recovery=expected_net,
        currency=currency,
        economically_viable=(expected_net is not None and expected_net > 0),
        reason="test",
        evidence={"probability_confidence": prob_conf},
    )


def test_no_viable_actions_returns_no_action():
    ctx = DecisionContext(
        context_version=1,
        generated_at=datetime.now(tz=timezone.utc),
        revenue_truth=make_rt(recoverable=Decimal("0")),
        diagnosis=make_diag(),
        action_candidates=[ActionCandidate(action="a", eligible=False, reason="", constraints={})],
        economic_evaluations=[econ("a", False, None)],
    )
    dr = run_decision_agent(ctx)
    assert dr.decision == "NO_ACTION"


def test_one_viable_action_recommend():
    ctx = DecisionContext(
        context_version=2,
        generated_at=datetime.now(tz=timezone.utc),
        revenue_truth=make_rt(recoverable=Decimal("100")),
        diagnosis=make_diag(),
        action_candidates=[ActionCandidate(action="retry", eligible=True, reason="", constraints={})],
        economic_evaluations=[econ("retry", True, "50")],
    )
    dr = run_decision_agent(ctx)
    assert dr.decision == "RECOMMEND_ACTION"
    assert dr.recommended_action == "retry"
    assert dr.context_version == 2


def test_multiple_viable_selects_highest_expected_net():
    ctx = DecisionContext(
        context_version=3,
        generated_at=datetime.now(tz=timezone.utc),
        revenue_truth=make_rt(),
        diagnosis=make_diag(),
        action_candidates=[ActionCandidate(action="a1", eligible=True, reason="", constraints={}), ActionCandidate(action="a2", eligible=True, reason="", constraints={})],
        economic_evaluations=[econ("a1", True, "100"), econ("a2", True, "200")],
    )
    dr = run_decision_agent(ctx)
    assert dr.decision == "RECOMMEND_ACTION"
    assert dr.recommended_action == "a2"


def test_ineligible_action_cannot_be_selected():
    ctx = DecisionContext(
        context_version=4,
        generated_at=datetime.now(tz=timezone.utc),
        revenue_truth=make_rt(),
        diagnosis=make_diag(),
        action_candidates=[ActionCandidate(action="a", eligible=False, reason="", constraints={})],
        economic_evaluations=[econ("a", False, "100")],
    )
    dr = run_decision_agent(ctx)
    assert dr.decision == "NO_ACTION"


def test_economically_unviable_cannot_be_selected():
    # economically_viable False in econ
    e = econ("a", True, "0")
    e.economically_viable = False
    ctx = DecisionContext(
        context_version=5,
        generated_at=datetime.now(tz=timezone.utc),
        revenue_truth=make_rt(),
        diagnosis=make_diag(),
        action_candidates=[ActionCandidate(action="a", eligible=True, reason="", constraints={})],
        economic_evaluations=[e],
    )
    dr = run_decision_agent(ctx)
    assert dr.decision == "NO_ACTION"


def test_needs_review_when_low_confidence():
    e = econ("a", True, "100", prob_conf="low")
    ctx = DecisionContext(
        context_version=6,
        generated_at=datetime.now(tz=timezone.utc),
        revenue_truth=make_rt(),
        diagnosis=make_diag(conf="high"),
        action_candidates=[ActionCandidate(action="a", eligible=True, reason="", constraints={})],
        economic_evaluations=[e],
    )
    dr = run_decision_agent(ctx)
    assert dr.decision == "NEEDS_REVIEW"


def test_recommendation_matches_eligible_candidate():
    e = econ("a", True, "100")
    ctx = DecisionContext(
        context_version=7,
        generated_at=datetime.now(tz=timezone.utc),
        revenue_truth=make_rt(),
        diagnosis=make_diag(),
        action_candidates=[ActionCandidate(action="a", eligible=True, reason="", constraints={})],
        economic_evaluations=[e],
    )
    dr = run_decision_agent(ctx)
    assert dr.recommended_action == "a"


def test_stale_context_rejected():
    e = econ("a", True, "100")
    ctx = DecisionContext(
        context_version=8,
        generated_at=datetime.now(tz=timezone.utc),
        revenue_truth=make_rt(),
        diagnosis=make_diag(),
        action_candidates=[ActionCandidate(action="a", eligible=True, reason="", constraints={})],
        economic_evaluations=[e],
    )
    # create DecisionResult with mismatched version by invoking validation directly
    dr = DecisionResult(
        decision="NO_ACTION",
        recommended_action=None,
        context_version=9,
        decided_at=datetime.now(tz=timezone.utc),
        rationale="stale",
        evidence={},
        agent_version=AGENT_VERSION,
        confidence="low",
    )
    try:
        validate_decision_context(ctx.context_version, dr)
        assert False, "expected DecisionValidationError for stale decision"
    except DecisionValidationError:
        pass


def test_deterministic_repeatability_and_rationale():
    e1 = econ("a", True, "100")
    e2 = econ("b", True, "50")
    ctx = DecisionContext(
        context_version=10,
        generated_at=datetime.now(tz=timezone.utc),
        revenue_truth=make_rt(),
        diagnosis=make_diag(),
        action_candidates=[ActionCandidate(action="a", eligible=True, reason="", constraints={}), ActionCandidate(action="b", eligible=True, reason="", constraints={})],
        economic_evaluations=[e1, e2],
    )
    dr1 = run_decision_agent(ctx)
    dr2 = run_decision_agent(ctx)
    assert dr1.decision == dr2.decision
    assert dr1.recommended_action == dr2.recommended_action
    assert isinstance(dr1.rationale, str) and dr1.rationale


def test_graph_is_langgraph_compiled():
    import app.agents.decision_agent as da
    # compiled graph should be a LangGraph compiled graph object
    cg = getattr(da, "_compiled_graph", None)
    assert cg is not None
    # ensure the compiled graph comes from the langgraph package
    assert cg.__class__.__module__.startswith("langgraph")
