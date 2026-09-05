from decimal import Decimal
import datetime
from fastapi.testclient import TestClient

from app.main import app
from app.db.models import Order, Payment
from app.services.recovery_pipeline import process_recovery_pipeline, MockDefaultProvider
from app.domain.states import RecoveryStatus

def test_get_nonexistent_recovery_case_returns_404(client):
    res = client.get("/api/recovery-cases/999999")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"]


def test_get_verifying_recovery_case_details(client, db_session):
    db = db_session
    order = Order(merchant_id=1, external_id="ord_api_verif", amount_total=Decimal("100.00"), currency="USD")
    db.add(order)
    db.commit()

    payment = Payment(
        merchant_id=1,
        provider_payment_id="pay_api_verif",
        amount=Decimal("100.00"),
        currency="USD",
        status="failed",
        provider_state="failed",
        provider_event_id="evt_api_verif",
        provider_state_at=datetime.datetime.now(tz=datetime.timezone.utc),
        order_id=order.id,
    )
    db.add(payment)
    db.commit()

    provider = MockDefaultProvider(behavior="success", provider_reference="pay_api_verif")
    case = process_recovery_pipeline(db, merchant_id=1, payment_id=payment.id, order_id=order.id, provider=provider)
    assert case is not None

    res = client.get(f"/api/recovery-cases/{case.id}")
    assert res.status_code == 200

    data = res.json()
    assert data["case_id"] == case.id
    assert data["status"] in ("VERIFYING", "NO_ACTION", "ESCALATED", "ABORTED", "RECOVERED")
    assert data["merchant_id"] == 1
    assert data["order_id"] == order.id
    assert data["payment_id"] == payment.id
    assert data["order_external_id"] == "ord_api_verif"
    assert data["provider_payment_id"] == "pay_api_verif"
    assert data["diagnosis"] == "PAYMENT_FAILURE"
    assert data["context_version"] == 1
    assert "audit_events" in data
    assert len(data["audit_events"]) > 0
    assert "decision_snapshot" in data
    assert "current_state" in data
    assert data["decision_snapshot"]["recoverable_amount"] == "100.0000"

    # Verify no secret fields exist in JSON response
    res_text = res.text.lower()
    assert "secret" not in res_text
    assert "token" not in res_text
    assert "password" not in res_text


def test_get_recovered_case_preserves_decision_snapshot_vs_current_state(client, db_session):
    db = db_session
    order = Order(merchant_id=1, external_id="ord_api_rec", amount_total=Decimal("250.00"), currency="USD")
    db.add(order)
    db.commit()

    stale_time = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(minutes=35)
    payment = Payment(
        merchant_id=1,
        provider_payment_id="pay_api_rec",
        amount=Decimal("250.00"),
        currency="USD",
        status="authorized",
        provider_state="authorized",
        provider_event_id="evt_api_auth",
        provider_state_at=stale_time,
        order_id=order.id,
    )
    db.add(payment)
    db.commit()

    provider = MockDefaultProvider(behavior="success", provider_reference="pay_api_rec")
    c1 = process_recovery_pipeline(db, merchant_id=1, payment_id=payment.id, order_id=order.id, trigger_reason="AUTHORIZATION_STALE", provider=provider)
    assert c1 is not None
    assert c1.status == RecoveryStatus.VERIFYING

    # Check case details before capture (VERIFYING)
    res_before = client.get(f"/api/recovery-cases/{c1.id}")
    assert res_before.status_code == 200
    data_before = res_before.json()
    assert data_before["decision_snapshot"]["recoverable_amount"] == "250.0000"
    assert data_before["current_state"]["case_status"] == "VERIFYING"

    # Payment becomes captured
    payment.provider_state = "captured"
    db.add(payment)
    db.commit()

    c2 = process_recovery_pipeline(db, merchant_id=1, payment_id=payment.id, order_id=order.id, trigger_reason="PAYMENT_CAPTURED", provider=provider)
    assert c2 is not None
    assert c2.status == RecoveryStatus.RECOVERED

    # Check case details after capture (RECOVERED)
    res_after = client.get(f"/api/recovery-cases/{c2.id}")
    assert res_after.status_code == 200

    data_after = res_after.json()
    assert data_after["case_id"] == c2.id
    assert data_after["status"] == "RECOVERED"

    # 1. Decision snapshot remains unchanged
    snap = data_after["decision_snapshot"]
    assert snap["recoverable_amount"] == "250.0000"
    assert snap["recommended_action"] == "attempt_capture_retry"
    assert snap["diagnosis"] == "AUTHORIZATION_STALE"

    # 2. Current state reflects captured payment and zero remaining recoverable amount
    curr = data_after["current_state"]
    assert curr["case_status"] == "RECOVERED"
    assert curr["payment_state"] == "captured"
    assert Decimal(curr["recoverable_amount"]) == Decimal("0.00")

    # 3. Selected action is NEVER displayed as INELIGIBLE
    evals = snap["action_evaluations"]
    selected = [e for e in evals if e["is_selected"]]
    assert len(selected) == 1
    assert selected[0]["action"] == "attempt_capture_retry"
    assert selected[0]["eligible"] is True
    assert selected[0]["economically_viable"] is True
    assert selected[0]["why_not"] is None


def test_economic_arithmetic_consistency_across_decision_snapshot(client, db_session):
    """Explicitly verify arithmetic consistency invariant across:

    - action_evaluations.expected_net_recovery
    - action_evaluations.success_probability
    - action_evaluations.intervention_cost
    - decision_rationale numeric value
    """
    db = db_session
    order = Order(merchant_id=1, external_id="ord_demo_econ", amount_total=Decimal("199.99"), currency="USD")
    db.add(order)
    db.commit()

    stale_time = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(minutes=35)
    payment = Payment(
        merchant_id=1,
        provider_payment_id="pay_demo_econ",
        amount=Decimal("199.99"),
        currency="USD",
        status="authorized",
        provider_state="authorized",
        provider_event_id="evt_demo_econ",
        provider_state_at=stale_time,
        order_id=order.id,
    )
    db.add(payment)
    db.commit()

    provider = MockDefaultProvider(behavior="success", provider_reference="pay_demo_econ")
    c = process_recovery_pipeline(db, merchant_id=1, payment_id=payment.id, order_id=order.id, trigger_reason="AUTHORIZATION_STALE", provider=provider)
    assert c is not None

    res = client.get(f"/api/recovery-cases/{c.id}")
    assert res.status_code == 200

    data = res.json()
    snap = data["decision_snapshot"]
    evals = snap["action_evaluations"]
    selected = [e for e in evals if e["is_selected"]][0]

    rec_amt = Decimal(snap["recoverable_amount"])
    prob = Decimal(str(selected["success_probability"]))
    cost = Decimal(selected["intervention_cost"])
    exp_net = Decimal(selected["expected_net_recovery"])

    # 1. Arithmetic Invariant Verification
    expected_recovered = (rec_amt * prob).quantize(Decimal("0.01"))
    calculated_exp_net = (expected_recovered - cost).quantize(Decimal("0.01"))
    assert exp_net == calculated_exp_net, f"Expected net recovery {exp_net} does not match calculated {calculated_exp_net}"

    # 2. Decision rationale numeric consistency
    rationale = snap["decision_rationale"]
    assert str(exp_net) in rationale, f"Decision rationale '{rationale}' does not contain expected net recovery '{exp_net}'"
