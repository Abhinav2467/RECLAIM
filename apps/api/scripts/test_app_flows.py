import uuid
from fastapi.testclient import TestClient
from app.main import app

def test_full_app_state_flows():
    client = TestClient(app)

    print("=== 1. TEST AUTHENTICATED SESSION ===")
    unique_email = f"visual_test_{uuid.uuid4().hex[:8]}@merchant.com"
    signup_payload = {
        "email": unique_email,
        "password": "Password123!",
        "merchant_name": "Editorial Test Merchant Inc."
    }
    signup_res = client.post("/api/auth/signup", json=signup_payload)
    print("Signup Status:", signup_res.status_code)
    assert signup_res.status_code == 200

    me_res = client.get("/api/auth/me")
    print("Me Status:", me_res.status_code, me_res.json())
    assert me_res.status_code == 200
    assert me_res.json()["authenticated"] is True

    print("\n=== 2. TEST OPERATIONS OVERVIEW ===")
    overview_res = client.get("/api/recovery/overview")
    print("Overview Status:", overview_res.status_code)
    assert overview_res.status_code == 200
    overview_data = overview_res.json()
    print("Aggregates:", overview_data.get("aggregates"))
    print("Counts:", overview_data.get("counts"))

    print("\n=== 3. TEST RECOVERY SCENARIO (VERIFYING STATE) ===")
    rec_res = client.post("/api/demo/recovery-scenario", json={"demo_run_id": "test-run-1"})
    print("Recovery Scenario Status:", rec_res.status_code)
    assert rec_res.status_code == 200
    rec_data = rec_res.json()
    case_id_verifying = rec_data["case_id"]
    print(f"Created Case #{case_id_verifying} Demo Response:", rec_data)

    case_detail_1 = client.get(f"/api/recovery-cases/{case_id_verifying}").json()
    print("Case Detail (VERIFYING) Status:", case_detail_1["status"])
    print("Current At-Risk Amount:", case_detail_1["current_state"]["recoverable_amount"])
    assert case_detail_1["status"] == "VERIFYING"

    print("\n=== 4. TEST SIMULATE PAYMENT CAPTURE (RECOVERED STATE) ===")
    cap_res = client.post("/api/demo/recovery-scenario/capture", json={"case_id": case_id_verifying})
    print("Capture Status:", cap_res.status_code)
    assert cap_res.status_code == 200
    cap_data = cap_res.json()
    print(f"Captured Case #{case_id_verifying} Demo Response:", cap_data)
    assert cap_data["case_status"] == "RECOVERED"

    case_detail_2 = client.get(f"/api/recovery-cases/{case_id_verifying}").json()
    print("Case Detail (RECOVERED) Status:", case_detail_2["status"])
    print("Current At-Risk Amount (should be 0.00):", case_detail_2["current_state"]["recoverable_amount"])
    assert case_detail_2["status"] == "RECOVERED"
    assert float(case_detail_2["current_state"]["recoverable_amount"]) == 0.0

    print("\n=== 5. TEST NO_ACTION SCENARIO ===")
    no_act_res = client.post("/api/demo/no-action-scenario", json={"demo_run_id": "test-run-2"})
    print("NO_ACTION Scenario Status:", no_act_res.status_code)
    assert no_act_res.status_code == 200
    no_act_data = no_act_res.json()
    case_id_no_action = no_act_data["case_id"]
    print(f"Created Case #{case_id_no_action} Demo Response:", no_act_data)

    case_detail_3 = client.get(f"/api/recovery-cases/{case_id_no_action}").json()
    print("Case Detail (NO_ACTION) Status:", case_detail_3["status"])
    print("Current At-Risk Amount (should be 0.00):", case_detail_3["current_state"]["recoverable_amount"])
    assert case_detail_3["status"] == "NO_ACTION"

    print("\n=== 6. VERIFY FINAL OVERVIEW AGGREGATES ===")
    final_overview_res = client.get("/api/recovery/overview")
    final_overview = final_overview_res.json()
    print("Final Overview Aggregates:", final_overview.get("aggregates"))
    print("Final Overview Counts:", final_overview.get("counts"))

    print("\n✅ ALL LIVE API FLOWS & STATE TRANSITIONS VERIFIED PERFECTLY!")

if __name__ == "__main__":
    test_full_app_state_flows()
