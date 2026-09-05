from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.domain.decision import (
    DecisionContext,
    DecisionResult,
    validate_decision_context,
    validate_decision_against_context,
    DecisionValidationError,
)
from app.domain.revenue_truth import RevenueTruthResult
from app.domain.diagnosis import DiagnosisResult
from app.domain.actions import ActionCandidate
from app.domain.economics import EconomicEvaluation


def make_rt():
    return RevenueTruthResult(
        order_id=123,
        expected_amount=Decimal("100"),
        captured_amount=Decimal("0"),
        currency="USD",
        recoverable_amount=Decimal("100"),
        resolution="complete",
        contributing_payments=[],
    )


def make_diag(code="PAYMENT_FAILURE"):
    now = datetime.now(tz=timezone.utc)
    return DiagnosisResult(
        diagnosis=code,
        confidence="high",
        order_id=123,
        payment_ids=[],
        evidence={},
        suggested_actions=[],
        diagnosis_timestamp=now,
    )


def make_candidate(action, eligible=True):
    return ActionCandidate(action=action, eligible=eligible, reason="test", constraints={})


def make_econ(action, eligible=True):
    return EconomicEvaluation(
        action=action,
        eligible=eligible,
        recoverable_amount=Decimal("100"),
        success_probability=Decimal("0.5"),
        expected_recovered_amount=Decimal("50.00"),
        intervention_cost=Decimal("1.00"),
        expected_net_recovery=Decimal("49.00"),
        currency="USD",
        economically_viable=True,
        reason="test",
        evidence={},
    )


def test_valid_decision_context_construction():
    rt = make_rt()
    d = make_diag()
    gen_at = datetime.now(tz=timezone.utc)
    ctx = DecisionContext(
        context_version=1,
        generated_at=gen_at,
        revenue_truth=rt,
        diagnosis=d,
        action_candidates=[make_candidate("notify_customer_failure")],
        economic_evaluations=[make_econ("notify_customer_failure")],
    )
    assert ctx.context_version == 1
    assert ctx.case_id == 123


def test_valid_decision_result_construction_and_validation():
    decided_at = datetime.now(tz=timezone.utc)
    dr = DecisionResult(
        decision="NO_ACTION",
        recommended_action=None,
        context_version=1,
        decided_at=decided_at,
        rationale="Nothing to do",
        evidence={},
        agent_version="agent-1",
        confidence="medium",
    )
    assert validate_decision_context(1, dr) is True


def test_recommend_action_requires_action():
    decided_at = datetime.now(tz=timezone.utc)
    try:
        DecisionResult(
            decision="RECOMMEND_ACTION",
            recommended_action=None,
            context_version=1,
            decided_at=decided_at,
            rationale="choose something",
            evidence={},
            agent_version="agent-1",
            confidence="high",
        )
        assert False, "expected DecisionValidationError"
    except DecisionValidationError:
        pass


def test_no_action_and_needs_review_accept_action_none():
    decided_at = datetime.now(tz=timezone.utc)
    DecisionResult(
        decision="NO_ACTION",
        recommended_action=None,
        context_version=1,
        decided_at=decided_at,
        rationale="ok",
        evidence={},
        agent_version="agent-1",
        confidence="low",
    )
    DecisionResult(
        decision="NEEDS_REVIEW",
        recommended_action=None,
        context_version=1,
        decided_at=decided_at,
        rationale="review",
        evidence={},
        agent_version="agent-1",
        confidence="low",
    )


def test_recommendation_must_match_eligible_candidate():
    rt = make_rt()
    d = make_diag()
    gen_at = datetime.now(tz=timezone.utc)
    ctx = DecisionContext(
        context_version=2,
        generated_at=gen_at,
        revenue_truth=rt,
        diagnosis=d,
        action_candidates=[make_candidate("notify_customer_failure", eligible=True), make_candidate("attempt_capture_retry", eligible=False)],
        economic_evaluations=[make_econ("notify_customer_failure")],
    )
    decided_at = datetime.now(tz=timezone.utc)
    dr = DecisionResult(
        decision="RECOMMEND_ACTION",
        recommended_action="notify_customer_failure",
        context_version=2,
        decided_at=decided_at,
        rationale="best candidate",
        evidence={},
        agent_version="agent-1",
        confidence="high",
    )
    assert validate_decision_against_context(dr, ctx) is True


def test_ineligible_candidate_cannot_be_recommended():
    rt = make_rt()
    d = make_diag()
    gen_at = datetime.now(tz=timezone.utc)
    ctx = DecisionContext(
        context_version=3,
        generated_at=gen_at,
        revenue_truth=rt,
        diagnosis=d,
        action_candidates=[make_candidate("attempt_capture_retry", eligible=False)],
        economic_evaluations=[make_econ("attempt_capture_retry", eligible=False)],
    )
    decided_at = datetime.now(tz=timezone.utc)
    dr = DecisionResult(
        decision="RECOMMEND_ACTION",
        recommended_action="attempt_capture_retry",
        context_version=3,
        decided_at=decided_at,
        rationale="try anyway",
        evidence={},
        agent_version="agent-1",
        confidence="low",
    )
    try:
        validate_decision_against_context(dr, ctx)
        assert False, "expected DecisionValidationError for ineligible candidate"
    except DecisionValidationError:
        pass


def test_stale_context_rejected_and_matching_accepted():
    decided_at = datetime.now(tz=timezone.utc)
    dr = DecisionResult(
        decision="NO_ACTION",
        recommended_action=None,
        context_version=5,
        decided_at=decided_at,
        rationale="stale test",
        evidence={},
        agent_version="agent-1",
        confidence="low",
    )
    try:
        validate_decision_context(4, dr)
        assert False, "expected stale rejection"
    except DecisionValidationError:
        pass
    assert validate_decision_context(5, dr) is True


def test_context_version_must_be_positive():
    rt = make_rt()
    d = make_diag()
    try:
        DecisionContext(
            context_version=0,
            generated_at=datetime.now(tz=timezone.utc),
            revenue_truth=rt,
            diagnosis=d,
            action_candidates=[],
            economic_evaluations=[],
        )
        assert False, "expected validation error for context_version"
    except DecisionValidationError:
        pass


def test_timestamps_timezone_aware_required():
    rt = make_rt()
    d = make_diag()
    naive = datetime.now()
    try:
        DecisionContext(
            context_version=1,
            generated_at=naive,
            revenue_truth=rt,
            diagnosis=d,
            action_candidates=[],
            economic_evaluations=[],
        )
        assert False, "expected timezone validation"
    except DecisionValidationError:
        pass


def test_decision_result_cannot_authorize_execution():
    # DecisionResult is only a recommendation; ensure no field implies execution
    decided_at = datetime.now(tz=timezone.utc)
    dr = DecisionResult(
        decision="NO_ACTION",
        recommended_action=None,
        context_version=1,
        decided_at=decided_at,
        rationale="ok",
        evidence={},
        agent_version="agent-1",
        confidence="low",
    )
    # there is no 'approved' or 'execute' field
    assert not hasattr(dr, "approved")
    assert not hasattr(dr, "execute")
