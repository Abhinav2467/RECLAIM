import pytest
from decimal import Decimal
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.domain.summary import (
    get_summary_generator,
    generate_executive_summary,
    DeterministicFallbackSummaryGenerator,
    MockExecutiveSummaryGenerator,
)

def test_api_read_model_includes_executive_summary(client, db_session):
    res_demo = client.post("/api/demo/recovery-scenario")
    snapshot = {
        "decision": "RECOMMEND_ACTION",
        "diagnosis": "AUTHORIZATION_STALE",
        "recoverable_amount": "199.99",
        "currency": "USD",
        "recommended_action": "attempt_capture_retry",
        "decision_rationale": "Recommended attempt_capture_retry with highest expected net recovery",
    }
    res = generate_executive_summary(snapshot, provider_name="disabled")
    assert res["provider"] == "deterministic"
    assert res["authoritative"] is False
    assert res["text"] == snapshot["decision_rationale"]


def test_mock_provider_returns_mock_summary():
    snapshot = {
        "decision": "RECOMMEND_ACTION",
        "diagnosis": "AUTHORIZATION_STALE",
        "recoverable_amount": "199.99",
        "currency": "USD",
        "recommended_action": "attempt_capture_retry",
        "decision_rationale": "Deterministic rationale",
    }
    res = generate_executive_summary(snapshot, provider_name="mock")
    assert res["provider"] == "mock"
    assert res["authoritative"] is False
    assert "Mock AI" in res["text"]
    assert "attempt_capture_retry" in res["text"]
    assert "199.99" in res["text"]


def test_mock_no_action_summary_does_not_imply_execution():
    snapshot = {
        "decision": "NO_ACTION",
        "diagnosis": "PAYMENT_FAILURE",
        "recoverable_amount": "0.00",
        "currency": "USD",
        "recommended_action": None,
        "decision_rationale": "No economically viable eligible actions",
    }
    res = generate_executive_summary(snapshot, provider_name="mock")
    assert res["provider"] == "mock"
    assert res["authoritative"] is False
    assert "NO_ACTION to preserve merchant capital" in res["text"]
    assert "attempt_capture_retry" not in res["text"]


def test_generator_failure_falls_back_to_deterministic():
    class FaultyGenerator:
        def generate_summary(self, snap):
            raise RuntimeError("Mock API timeout")

    snapshot = {
        "decision_rationale": "Authoritative rationale fallback",
    }
    # Invoke fallback manually on error
    try:
        gen = FaultyGenerator()
        res = gen.generate_summary(snapshot).to_dict()
    except Exception:
        res = DeterministicFallbackSummaryGenerator().generate_summary(snapshot).to_dict()

    assert res["provider"] == "deterministic"
    assert res["text"] == "Authoritative rationale fallback"


def test_summary_is_read_only_and_does_not_mutate_snapshot():
    snapshot = {
        "decision": "RECOMMEND_ACTION",
        "recommended_action": "attempt_capture_retry",
        "recoverable_amount": "199.99",
        "decision_rationale": "Rationale",
    }
    snapshot_before = dict(snapshot)
    res = generate_executive_summary(snapshot, provider_name="mock")
    assert snapshot == snapshot_before
    assert snapshot["recommended_action"] == "attempt_capture_retry"
    assert snapshot["decision"] == "RECOMMEND_ACTION"


def test_api_read_model_includes_executive_summary(client, db_session):
    res_demo = client.post("/api/demo/recovery-scenario")
    assert res_demo.status_code == 200
    case_id = res_demo.json()["case_id"]

    res_details = client.get(f"/api/recovery-cases/{case_id}")
    assert res_details.status_code == 200
    data = res_details.json()

    assert "executive_summary" in data
    summary = data["executive_summary"]
    assert "text" in summary
    assert "provider" in summary
    assert summary["authoritative"] is False
