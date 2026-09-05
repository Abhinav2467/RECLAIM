import uuid
from decimal import Decimal
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.db.models import Order, Payment, RecoveryCase, ExecutionRecord

def test_demo_scenario_fresh_run_uniqueness_and_capture(client, db_session):
    """Test fresh-run uniqueness: two different demo_run_ids produce isolated cases."""
    run_id_a = str(uuid.uuid4())
    run_id_b = str(uuid.uuid4())

    # 1. Trigger run A
    res_a = client.post("/api/demo/recovery-scenario", json={"demo_run_id": run_id_a})
    assert res_a.status_code == 200
    data_a = res_a.json()
    assert data_a["status"] == "success"
    assert data_a["demo_run_id"] == run_id_a
    assert data_a["case_status"] == "VERIFYING"

    case_id_a = data_a["case_id"]
    order_ext_a = data_a["order_external_id"]
    pay_ext_a = data_a["provider_payment_id"]

    # 2. Trigger run B
    res_b = client.post("/api/demo/recovery-scenario", json={"demo_run_id": run_id_b})
    assert res_b.status_code == 200
    data_b = res_b.json()
    assert data_b["status"] == "success"
    assert data_b["demo_run_id"] == run_id_b

    case_id_b = data_b["case_id"]
    order_ext_b = data_b["order_external_id"]
    pay_ext_b = data_b["provider_payment_id"]

    # Verify complete isolation
    assert case_id_a != case_id_b
    assert order_ext_a != order_ext_b
    assert pay_ext_a != pay_ext_b

    # Database checks
    order_a = db_session.query(Order).filter(Order.external_id == order_ext_a).first()
    order_b = db_session.query(Order).filter(Order.external_id == order_ext_b).first()
    assert order_a is not None and order_b is not None
    assert order_a.id != order_b.id

    payment_a = db_session.query(Payment).filter(Payment.provider_payment_id == pay_ext_a).first()
    payment_b = db_session.query(Payment).filter(Payment.provider_payment_id == pay_ext_b).first()
    assert payment_a is not None and payment_b is not None
    assert payment_a.id != payment_b.id


def test_demo_scenario_same_run_idempotency(client, db_session):
    """Test same-run idempotency: repeating the same demo_run_id returns the existing case."""
    run_id = str(uuid.uuid4())

    # Call 1
    res1 = client.post("/api/demo/recovery-scenario", json={"demo_run_id": run_id})
    assert res1.status_code == 200
    data1 = res1.json()
    case_id1 = data1["case_id"]
    order_ext = data1["order_external_id"]

    # Call 2 with identical demo_run_id
    res2 = client.post("/api/demo/recovery-scenario", json={"demo_run_id": run_id})
    assert res2.status_code == 200
    data2 = res2.json()
    case_id2 = data2["case_id"]

    assert case_id1 == case_id2
    assert data1["demo_run_id"] == data2["demo_run_id"]

    # Verify no duplicate order, payment, case, or execution record was created
    orders = db_session.query(Order).filter(Order.external_id == order_ext).all()
    assert len(orders) == 1

    cases = db_session.query(RecoveryCase).filter(RecoveryCase.order_id == orders[0].id).all()
    assert len(cases) == 1

    exec_records = db_session.query(ExecutionRecord).filter(ExecutionRecord.recovery_case_id == case_id1).all()
    assert len(exec_records) == 1


def test_demo_scenario_capture_isolation(client, db_session):
    """Test capture isolation: capturing run A leaves run B uncaptured in VERIFYING state."""
    run_id_a = str(uuid.uuid4())
    run_id_b = str(uuid.uuid4())

    res_a = client.post("/api/demo/recovery-scenario", json={"demo_run_id": run_id_a})
    case_id_a = res_a.json()["case_id"]

    res_b = client.post("/api/demo/recovery-scenario", json={"demo_run_id": run_id_b})
    case_id_b = res_b.json()["case_id"]

    # Capture run A specifically
    res_cap = client.post("/api/demo/recovery-scenario/capture", json={"demo_run_id": run_id_a, "case_id": case_id_a})
    assert res_cap.status_code == 200
    cap_data = res_cap.json()
    assert cap_data["case_id"] == case_id_a
    assert cap_data["case_status"] == "RECOVERED"
    assert cap_data["verification_outcome"] == "RECOVERED"

    # Verify run A is RECOVERED in DB
    db_session.expire_all()
    case_a = db_session.get(RecoveryCase, case_id_a)
    assert case_a.status == "RECOVERED"

    # Verify run B remains in VERIFYING state with PENDING verification_outcome
    case_b = db_session.get(RecoveryCase, case_id_b)
    assert case_b.status == "VERIFYING"
    assert case_b.verification_outcome == "PENDING"


def test_demo_no_action_scenario_uniqueness_and_idempotency(client, db_session):
    """Test NO_ACTION scenario with fresh run uniqueness and same-run idempotency."""
    run_id_1 = str(uuid.uuid4())
    run_id_2 = str(uuid.uuid4())

    # Run 1
    res1 = client.post("/api/demo/no-action-scenario", json={"demo_run_id": run_id_1})
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["status"] == "success"
    assert data1["case_status"] == "NO_ACTION"
    assert data1["recommended_action"] is None
    case_id_1 = data1["case_id"]

    # Run 2 (different run_id)
    res2 = client.post("/api/demo/no-action-scenario", json={"demo_run_id": run_id_2})
    assert res2.status_code == 200
    data2 = res2.json()
    case_id_2 = data2["case_id"]

    assert case_id_1 != case_id_2

    # Repeat Run 1 (idempotency check)
    res1_repeat = client.post("/api/demo/no-action-scenario", json={"demo_run_id": run_id_1})
    assert res1_repeat.status_code == 200
    assert res1_repeat.json()["case_id"] == case_id_1


def test_economically_unjustified_no_action_has_revenue_at_risk(client, db_session):
    """Test that economically unjustified NO_ACTION scenario has revenue at risk > $0."""
    run_id = str(uuid.uuid4())
    res = client.post("/api/demo/no-action-scenario", json={"demo_run_id": run_id})
    assert res.status_code == 200
    data = res.json()
    assert data["case_status"] == "NO_ACTION"
    assert Decimal(data["amount"]) > Decimal("0")

    # Fetch full case details
    c_res = client.get(f"/api/recovery-cases/{data['case_id']}")
    assert c_res.status_code == 200
    c_data = c_res.json()
    assert Decimal(c_data["recoverable_amount"]) > Decimal("0")
    assert c_data["status"] == "NO_ACTION"
    assert c_data["recommended_action"] is None


def test_demo_checkout_abandonment_scenario(client, db_session):
    """Test checkout abandonment demo scenario creates case with cart recovery action."""
    run_id = str(uuid.uuid4())
    res = client.post("/api/demo/checkout-abandonment-scenario", json={"demo_run_id": run_id})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["scenario"] == "demo_checkout_abandonment"
    assert data["recommended_action"] == "send_cart_recovery_email"


def test_demo_showcase_batch_creation(client, db_session):
    """Test seeding showcase batch creates 6 diverse demo cases idempotently."""
    batch_id = str(uuid.uuid4())
    res = client.post("/api/demo/batch", json={"batch_run_id": batch_id})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["total_cases_created"] == 6
    assert len(data["cases"]) == 6

    # Test idempotency on same batch_run_id
    res_repeat = client.post("/api/demo/batch", json={"batch_run_id": batch_id})
    assert res_repeat.status_code == 200
    assert res_repeat.json()["total_cases_created"] == 6


def test_production_environment_guard_blocks_demo_endpoints(client, monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")

    res1 = client.post("/api/demo/recovery-scenario")
    assert res1.status_code == 403
    assert "disabled in production" in res1.json()["detail"]

    res2 = client.post("/api/demo/recovery-scenario/capture")
    assert res2.status_code == 403
    assert "disabled in production" in res2.json()["detail"]

    res3 = client.post("/api/demo/no-action-scenario")
    assert res3.status_code == 403
    assert "disabled in production" in res3.json()["detail"]

    res4 = client.post("/api/demo/batch")
    assert res4.status_code == 403
    assert "disabled in production" in res4.json()["detail"]
