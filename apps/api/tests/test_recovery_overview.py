import uuid
from decimal import Decimal
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings

from app.db.models import Merchant, User
from app.core.security import hash_password

def test_empty_merchant_overview(db_session):
    """Test 1: Empty merchant overview returns 0 counts and 0.00 aggregates."""
    m = db_session.get(Merchant, 999999)
    if not m:
        m = Merchant(id=999999, name="Empty Merchant")
        db_session.add(m)
        db_session.commit()

    email = f"empty_{uuid.uuid4().hex[:6]}@merchant.com"
    u = User(merchant_id=999999, email=email, password_hash=hash_password("Pass123!"))
    db_session.add(u)
    db_session.commit()

    tc = TestClient(app)
    tc.post("/api/auth/login", json={"email": email, "password": "Pass123!"})

    res = tc.get("/api/recovery/overview")
    assert res.status_code == 200
    data = res.json()

    assert data["merchant_id"] == 999999
    counts = data["counts"]
    assert counts["total_cases"] == 0
    assert counts["active_cases"] == 0
    assert counts["verifying_cases"] == 0
    assert counts["recovered_cases"] == 0
    assert counts["no_action_cases"] == 0
    assert counts["failed_cases"] == 0

    aggregates = data["aggregates"]
    assert aggregates["revenue_at_risk"] == "0.00"
    assert aggregates["recovered_amount"] == "0.00"
    assert aggregates["expected_recovery"] == "0.00"
    assert aggregates["capital_preserved"] == "0.00"
    assert data["cases"] == []


def test_overview_one_active_verifying_case(client, db_session):
    """Test 2: One active VERIFYING case is correctly aggregated."""
    run_id = str(uuid.uuid4())
    res_setup = client.post("/api/demo/recovery-scenario", json={"demo_run_id": run_id})
    assert res_setup.status_code == 200

    res = client.get("/api/recovery/overview")
    assert res.status_code == 200
    data = res.json()

    counts = data["counts"]
    assert counts["verifying_cases"] >= 1
    assert counts["active_cases"] >= 1

    aggregates = data["aggregates"]
    assert Decimal(aggregates["revenue_at_risk"]) > Decimal("0.00")
    assert Decimal(aggregates["expected_recovery"]) > Decimal("0.00")

    # Case ledger check
    case_ids = [c["case_id"] for c in data["cases"]]
    assert res_setup.json()["case_id"] in case_ids


def test_overview_recovered_and_active_cases_ledger(client, db_session):
    """Test 3: One RECOVERED case and one active case both appear in ledger."""
    run_id_rec = str(uuid.uuid4())
    run_id_act = str(uuid.uuid4())

    # Setup run A and capture it
    res_a = client.post("/api/demo/recovery-scenario", json={"demo_run_id": run_id_rec})
    case_id_a = res_a.json()["case_id"]
    res_cap = client.post("/api/demo/recovery-scenario/capture", json={"demo_run_id": run_id_rec, "case_id": case_id_a})
    assert res_cap.json()["case_status"] == "RECOVERED"

    # Setup run B (active VERIFYING)
    res_b = client.post("/api/demo/recovery-scenario", json={"demo_run_id": run_id_act})
    case_id_b = res_b.json()["case_id"]

    res = client.get("/api/recovery/overview")
    assert res.status_code == 200
    data = res.json()

    # Both cases appear in the ledger
    case_ids = [c["case_id"] for c in data["cases"]]
    assert case_id_a in case_ids
    assert case_id_b in case_ids

    # Recovered case aggregate is > 0
    aggregates = data["aggregates"]
    assert Decimal(aggregates["recovered_amount"]) > Decimal("0.00")

    # Historical expected recovery is preserved after recovery
    rec_case_item = next(c for c in data["cases"] if c["case_id"] == case_id_a)
    assert rec_case_item["status"] == "RECOVERED"
    assert rec_case_item["verification_outcome"] == "RECOVERED"
    assert Decimal(rec_case_item["decision_expected_net_recovery"]) > Decimal("0.00")
    assert rec_case_item["current_at_risk_amount"] == "0.00"


def test_overview_no_action_case_classification(client, db_session):
    """Test 4: NO_ACTION case is separately classified and preserves capital_preserved aggregate."""
    run_id_no_act = str(uuid.uuid4())
    res_no_act = client.post("/api/demo/no-action-scenario", json={"demo_run_id": run_id_no_act})
    assert res_no_act.status_code == 200
    case_id_no_act = res_no_act.json()["case_id"]

    res = client.get("/api/recovery/overview")
    assert res.status_code == 200
    data = res.json()

    counts = data["counts"]
    assert counts["no_action_cases"] >= 1

    no_act_item = next(c for c in data["cases"] if c["case_id"] == case_id_no_act)
    assert no_act_item["status"] == "NO_ACTION"
    assert no_act_item["current_at_risk_amount"] == "0.00"


def test_overview_multiple_demo_runs_independence(client, db_session):
    """Test 8: Multiple demo_run_id cases all appear independently in the overview."""
    run_id_1 = str(uuid.uuid4())
    run_id_2 = str(uuid.uuid4())
    run_id_3 = str(uuid.uuid4())

    c1 = client.post("/api/demo/recovery-scenario", json={"demo_run_id": run_id_1}).json()["case_id"]
    c2 = client.post("/api/demo/recovery-scenario", json={"demo_run_id": run_id_2}).json()["case_id"]
    c3 = client.post("/api/demo/no-action-scenario", json={"demo_run_id": run_id_3}).json()["case_id"]

    res = client.get("/api/recovery/overview")
    assert res.status_code == 200
    data = res.json()

    case_ids = [c["case_id"] for c in data["cases"]]
    assert c1 in case_ids
    assert c2 in case_ids
    assert c3 in case_ids
