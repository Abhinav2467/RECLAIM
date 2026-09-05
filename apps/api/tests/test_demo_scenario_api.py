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


def test_showcase_47_dollar_no_action_is_genuinely_unjustified(client, db_session):
    """Verify the $47 demo scenario is genuinely NO_ACTION with net recovery <= 0 for all eligible candidates."""
    run_id = f"test-no-action-47-{uuid.uuid4()}"
    res = client.post("/api/demo/no-action-scenario", json={"demo_run_id": run_id})
    assert res.status_code == 200
    data = res.json()
    assert data["case_status"] == "NO_ACTION"
    assert data["recommended_action"] is None
    assert data["amount"] == "47.00"

    c_res = client.get(f"/api/recovery-cases/{data['case_id']}")
    assert c_res.status_code == 200
    c_data = c_res.json()

    evals = c_data["decision_snapshot"]["action_evaluations"]
    eligible_evals = [e for e in evals if e["eligible"]]
    assert len(eligible_evals) > 0

    for e in eligible_evals:
        assert e["economically_viable"] is False
        assert Decimal(e["expected_net_recovery"]) <= Decimal("0.00")
        assert e["why_not"] == "Expected recovery does not exceed intervention cost"


def test_displayed_economics_equal_backend_decision_economics(client, db_session):
    """Verify that case detail action_evaluations use exact decision-time costs ($50.00) matching backend."""
    run_id = f"test-disp-econ-{uuid.uuid4()}"
    res = client.post("/api/demo/no-action-scenario", json={"demo_run_id": run_id})
    case_id = res.json()["case_id"]

    c_res = client.get(f"/api/recovery-cases/{case_id}")
    c_data = c_res.json()
    evals = c_data["decision_snapshot"]["action_evaluations"]
    notify_eval = next(e for e in evals if e["action"] == "notify_customer_failure")

    assert notify_eval["intervention_cost"] == "50.00"
    assert Decimal(notify_eval["expected_net_recovery"]) < Decimal("0.00")
    assert notify_eval["economically_viable"] is False


def test_final_decision_explanation_matches_decision_reason(client, db_session):
    """Verify that NO_ACTION decision rationale matches 'No economically viable eligible actions'."""
    run_id = f"test-explanation-{uuid.uuid4()}"
    res = client.post("/api/demo/no-action-scenario", json={"demo_run_id": run_id})
    case_id = res.json()["case_id"]

    c_res = client.get(f"/api/recovery-cases/{case_id}")
    c_data = c_res.json()
    snapshot = c_data["decision_snapshot"]
    assert snapshot["decision"] == "NO_ACTION"
    assert "No economically viable eligible actions" in snapshot["decision_rationale"]


def test_showcase_batch_full_6_scenarios_and_aggregates(client, db_session):
    """Verify seeding showcase batch creates 6 distinct unique showcase scenarios with exact expected amounts and statuses."""
    batch_id = f"test-batch-full-{uuid.uuid4()}"
    res = client.post("/api/demo/batch", json={"batch_run_id": batch_id})
    assert res.status_code == 200
    data = res.json()
    assert data["total_cases_created"] == 6

    cases = data["cases"]
    case_ids = [c["case_id"] for c in cases]
    assert len(set(case_ids)) == 6, "All 6 showcase case IDs must be distinct"

    # Fetch merchant recovery overview
    ov_res = client.get("/api/recovery/overview")
    assert ov_res.status_code == 200
    ov = ov_res.json()

    assert ov["counts"]["total_cases"] == 6
    assert ov["counts"]["verifying_cases"] == 3
    assert ov["counts"]["recovered_cases"] == 2
    assert ov["counts"]["no_action_cases"] == 1
    assert ov["counts"]["failed_cases"] == 0

    assert Decimal(ov["aggregates"]["recovered_amount"]) == Decimal("1588.00")  # 1499.00 + 89.00
    assert Decimal(ov["aggregates"]["capital_preserved"]) == Decimal("47.00")   # 47.00
    assert Decimal(ov["aggregates"]["revenue_at_risk"]) == Decimal("1349.00")   # 249.00 + 320.00 + 780.00


def test_all_showcase_scenarios_invariant_consistency(client, db_session):
    """Verify core invariants across all 6 showcase scenarios in the batch: backend decision == API snapshot == UI fields."""
    batch_id = f"test-invariants-{uuid.uuid4()}"
    res = client.post("/api/demo/batch", json={"batch_run_id": batch_id})
    cases = res.json()["cases"]

    for c_info in cases:
        cid = c_info["case_id"]
        scenario = c_info["scenario"]

        c_res = client.get(f"/api/recovery-cases/{cid}")
        assert c_res.status_code == 200
        c_data = c_res.json()

        snapshot = c_data["decision_snapshot"]
        current = c_data["current_state"]
        evals = c_data["action_evaluations"]

        # Invariant A: Displayed recoverable amount == decision-time recoverable amount
        assert Decimal(c_data["recoverable_amount"]) == Decimal(snapshot["recoverable_amount"])

        # Invariant F & G: Decision and rationale match snapshot
        assert c_data["decision"] == snapshot["decision"]
        assert c_data["decision_rationale"] == snapshot["decision_rationale"]

        if scenario == "economically_unjustified_no_action":
            # Invariant L: NO_ACTION economically unjustified must have expected_net <= 0 for all eligible candidates
            assert c_data["status"] == "NO_ACTION"
            assert c_data["recommended_action"] is None
            for e in evals:
                if e["eligible"]:
                    assert e["economically_viable"] is False
                    assert Decimal(e["expected_net_recovery"]) <= Decimal("0.00")
        elif scenario in {"auth_stale_recovered", "auth_stale_recovered_small"}:
            # Invariant K: RECOVERED appears ONLY when verification is RECOVERED
            assert c_data["status"] == "RECOVERED"
            assert current["verification_outcome"] == "RECOVERED"
            assert current["payment_state"] == "captured"
            assert Decimal(current["recoverable_amount"]) == Decimal("0.00")
        else:
            # Active verifying cases
            assert c_data["status"] == "VERIFYING"
            assert c_data["recommended_action"] is not None
            sel_eval = next(e for e in evals if e["is_selected"])
            # Invariant D & E: Gross & net recovery arithmetic
            rec_amt = Decimal(c_data["recoverable_amount"])
            prob = Decimal(str(sel_eval["success_probability"]))
            cost = Decimal(str(sel_eval["intervention_cost"]))
            expected_gross = rec_amt * prob
            expected_net = expected_gross - cost
            assert Decimal(sel_eval["expected_net_recovery"]) == expected_net


