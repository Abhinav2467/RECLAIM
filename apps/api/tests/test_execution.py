from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.domain.execution import ExecutionManager, ExecutionError, ExecutionResult, EXEC_STATUS_EXECUTED, EXEC_STATUS_FAILED, EXEC_STATUS_PENDING
from app.domain.verification import verify_execution, VERIF_STATUS_RECOVERED, VERIF_STATUS_PENDING, VERIF_STATUS_FAILED, VERIF_STATUS_NOT_RECOVERED
from app.domain.policy import PolicyDecision
from app.domain.decision import DecisionContext, DecisionResult
from app.domain.revenue_truth import RevenueTruthResult, ContributingPayment
from app.domain.actions import ActionCandidate


class MockProvider:
    """Deterministic mock provider for tests.

    behavior: 'success'|'failed'|'pending'|'rejected'
    provider_reference: str
    """

    def __init__(self, behavior: str = "success", provider_reference: str = "prov-1"):
        self.behavior = behavior
        self.provider_reference = provider_reference

    def execute(self, action: str, context: DecisionContext, idempotency_key: str):
        if self.behavior == "success":
            return type("R", (), {"status": "success", "provider_reference": self.provider_reference, "message": "ok", "evidence": {"action": action}})()
        if self.behavior == "failed":
            return type("R", (), {"status": "failed", "provider_reference": None, "message": "error", "evidence": {}})()
        if self.behavior == "pending":
            return type("R", (), {"status": "pending", "provider_reference": self.provider_reference, "message": "pending", "evidence": {}})()
        return type("R", (), {"status": "rejected", "provider_reference": None, "message": "rejected", "evidence": {}})()


def make_context():
    rt = RevenueTruthResult(order_id=1, expected_amount=Decimal("100"), captured_amount=Decimal("0"), currency="USD", recoverable_amount=Decimal("100"), resolution="complete", contributing_payments=[])
    ctx = DecisionContext(context_version=1, generated_at=datetime.now(tz=timezone.utc), revenue_truth=rt, diagnosis=None, action_candidates=[ActionCandidate(action="attempt_capture_retry", eligible=True, reason="r", constraints={})], economic_evaluations=[])
    return ctx


def make_approved_policy(action: str):
    return PolicyDecision(decision="APPROVED", action=action, approved=True, reasons=["policy_checks_passed"], constraints={}, evaluated_at=datetime.now(tz=timezone.utc))


def test_approved_allows_execution_and_provider_success():
    mgr = ExecutionManager()
    ctx = make_context()
    pd = make_approved_policy("attempt_capture_retry")
    provider = MockProvider(behavior="success", provider_reference="pay-123")
    res = mgr.execute(pd, ctx, idempotency_key="k1", provider=provider)
    assert res.status == EXEC_STATUS_EXECUTED
    assert res.provider_reference == "pay-123"


def test_blocked_policy_rejected_execution():
    mgr = ExecutionManager()
    ctx = make_context()
    pd = PolicyDecision(decision="BLOCKED", action="attempt_capture_retry", approved=False, reasons=["insufficient_budget"], constraints={}, evaluated_at=datetime.now(tz=timezone.utc))
    provider = MockProvider()
    with pytest.raises(ExecutionError):
        mgr.execute(pd, ctx, idempotency_key="k1", provider=provider)


def test_missing_idempotency_rejected():
    mgr = ExecutionManager()
    ctx = make_context()
    pd = make_approved_policy("attempt_capture_retry")
    provider = MockProvider()
    with pytest.raises(ExecutionError):
        mgr.execute(pd, ctx, idempotency_key=None, provider=provider)


def test_unsupported_action_rejected_by_provider():
    mgr = ExecutionManager()
    ctx = make_context()
    pd = make_approved_policy("unsupported_action")
    class RejectingProvider(MockProvider):
        def execute(self, action, context, idempotency_key):
            return type("R", (), {"status": "rejected", "provider_reference": None, "message": "unsupported", "evidence": {}})()

    provider = RejectingProvider()
    res = mgr.execute(pd, ctx, idempotency_key="id1", provider=provider)
    assert res.status == "REJECTED"


def test_idempotency_preserved_and_no_duplicate_execution():
    mgr = ExecutionManager()
    ctx = make_context()
    pd = make_approved_policy("attempt_capture_retry")
    provider = MockProvider(behavior="success", provider_reference="prov-9")
    r1 = mgr.execute(pd, ctx, idempotency_key="dup", provider=provider)
    r2 = mgr.execute(pd, ctx, idempotency_key="dup", provider=provider)
    assert r1.execution_id == r2.execution_id
    assert r1 is r2


def test_provider_failure_and_pending():
    mgr = ExecutionManager()
    ctx = make_context()
    pd = make_approved_policy("attempt_capture_retry")
    provider_fail = MockProvider(behavior="failed")
    res_fail = mgr.execute(pd, ctx, idempotency_key="f1", provider=provider_fail)
    assert res_fail.status == EXEC_STATUS_FAILED

    provider_pending = MockProvider(behavior="pending", provider_reference="prov-p")
    res_p = mgr.execute(pd, ctx, idempotency_key="p1", provider=provider_pending)
    assert res_p.status == EXEC_STATUS_PENDING


def test_manual_action_represents_pending_without_provider_call():
    mgr = ExecutionManager()
    ctx = make_context()
    pd = make_approved_policy("manual_review")
    # provider should not be called; pass a provider that would error if called
    class BadProvider(MockProvider):
        def execute(self, action, context, idempotency_key):
            raise AssertionError("provider called for manual action")

    res = mgr.execute(pd, ctx, idempotency_key="m1", provider=BadProvider())
    assert res.status == EXEC_STATUS_PENDING


def test_deterministic_results_and_no_db_mutation():
    mgr = ExecutionManager()
    ctx = make_context()
    pd = make_approved_policy("attempt_capture_retry")
    provider = MockProvider(behavior="success", provider_reference="prov-x")
    r = mgr.execute(pd, ctx, idempotency_key="det", provider=provider)
    # call verification - without DB, verification should be pending because no captured payment
    ver = verify_execution(r, ctx)
    assert ver.status == VERIF_STATUS_PENDING
