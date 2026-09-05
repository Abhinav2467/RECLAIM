import pytest
from app.integrations.razorpay_adapter import RazorpayRecoveryProvider
from app.domain.execution import ExecutionManager, EXEC_STATUS_REJECTED
from app.domain.policy import PolicyDecision
from app.domain.decision import DecisionContext, DecisionResult
from app.domain.revenue_truth import RevenueTruthResult
from app.domain.actions import ActionCandidate
from datetime import datetime, timezone
from decimal import Decimal


def make_dummy_context():
    rt = RevenueTruthResult(
        order_id=1,
        expected_amount=Decimal("100.00"),
        captured_amount=Decimal("0.00"),
        currency="USD",
        recoverable_amount=Decimal("100.00"),
        resolution="complete",
        contributing_payments=[],
    )
    return DecisionContext(
        context_version=1,
        generated_at=datetime.now(tz=timezone.utc),
        revenue_truth=rt,
        diagnosis=None,
        action_candidates=[ActionCandidate(action="attempt_capture_retry", eligible=True, reason="r", constraints={})],
        economic_evaluations=[],
    )


def make_approved_policy(action: str = "attempt_capture_retry"):
    return PolicyDecision(
        decision="APPROVED",
        action=action,
        approved=True,
        reasons=["ok"],
        constraints={},
        evaluated_at=datetime.now(tz=timezone.utc),
    )


def test_razorpay_adapter_satisfies_protocol():
    adapter = RazorpayRecoveryProvider(key_id="", key_secret="", enabled=False)
    assert hasattr(adapter, "execute")
    assert callable(adapter.execute)


def test_unconfigured_razorpay_adapter_produces_rejected_result():
    adapter = RazorpayRecoveryProvider(key_id="", key_secret="", enabled=False)
    ctx = make_dummy_context()

    res = adapter.execute("attempt_capture_retry", ctx, "k1")

    assert res.status == "rejected"
    assert res.provider_reference is None
    assert "not configured" in res.message
    assert res.evidence["configured"] is False


def test_configured_disabled_adapter_prevents_network_calls():
    adapter = RazorpayRecoveryProvider(key_id="key_test_123", key_secret="sec_test_456", enabled=False)
    ctx = make_dummy_context()

    res = adapter.execute("attempt_capture_retry", ctx, "k2")

    assert res.status == "rejected"
    assert res.provider_reference is None
    assert "disabled" in res.message
    assert res.evidence["live_network_enabled"] is False


def test_execution_manager_integrates_with_razorpay_adapter():
    mgr = ExecutionManager()
    ctx = make_dummy_context()
    pd = make_approved_policy("attempt_capture_retry")
    adapter = RazorpayRecoveryProvider(key_id="", key_secret="", enabled=False)

    exec_res = mgr.execute(pd, ctx, idempotency_key="rzp_k1", provider=adapter)

    assert exec_res.status == EXEC_STATUS_REJECTED
    assert exec_res.action == "attempt_capture_retry"
    assert exec_res.provider_reference is None
    assert "not configured" in exec_res.message


def test_unsupported_action_rejected_by_razorpay_adapter():
    adapter = RazorpayRecoveryProvider(key_id="key_test_123", key_secret="sec_test_456", enabled=False)
    ctx = make_dummy_context()

    res = adapter.execute("unsupported_custom_action", ctx, "k3")

    assert res.status == "rejected"
    assert "not supported" in res.message
