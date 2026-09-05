import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.db.models import Merchant, User, RecoveryCase, Order, Customer, Payment
from app.db.session import SessionLocal
from app.core.security import hash_password


def test_auth_signup_success_no_token_in_json():
    client = TestClient(app)
    email = f"signup_{uuid.uuid4().hex[:8]}@merchant.com"
    res = client.post("/api/auth/signup", json={
        "email": email,
        "password": "SecurePassword123!",
        "merchant_name": "Acme Payments Corp",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["user"]["email"] == email.lower()
    # Requirement A: Session token MUST NOT be returned in JSON payload
    assert "token" not in data
    assert "password" not in data["user"]
    assert "password_hash" not in data["user"]
    # HTTP-only session cookie is set
    assert "reclaim_session" in res.cookies


def test_auth_login_success_no_token_in_json():
    client = TestClient(app)
    email = f"login_{uuid.uuid4().hex[:8]}@merchant.com"
    password = "MySecretPassword123"
    res_signup = client.post("/api/auth/signup", json={"email": email, "password": password})
    assert res_signup.status_code == 200

    res_login = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res_login.status_code == 200
    # Requirement B: Session token MUST NOT be returned in JSON payload
    assert "token" not in res_login.json()
    assert "reclaim_session" in res_login.cookies
    assert res_login.json()["user"]["email"] == email
    assert "password_hash" not in res_login.json()["user"]


def test_auth_me_authenticated_and_unauthenticated():
    client = TestClient(app)
    # Requirement C: Unauthenticated -> 401
    res_unauth = client.get("/api/auth/me")
    assert res_unauth.status_code == 401
    assert res_unauth.json()["detail"] == "Not authenticated"

    # Requirement C: Authenticated -> 200
    email = f"me_{uuid.uuid4().hex[:8]}@merchant.com"
    signup_res = client.post("/api/auth/signup", json={"email": email, "password": "Password123!"})
    assert signup_res.status_code == 200

    res_me = client.get("/api/auth/me")
    assert res_me.status_code == 200
    assert res_me.json()["authenticated"] is True
    assert res_me.json()["user"]["email"] == email


def test_operations_overview_authorization():
    client = TestClient(app)
    # Requirement D: Unauthenticated -> 401
    res_unauth = client.get("/api/recovery/overview")
    assert res_unauth.status_code == 401

    # Requirement D: Authenticated -> 200
    email = f"overview_{uuid.uuid4().hex[:8]}@merchant.com"
    client.post("/api/auth/signup", json={"email": email, "password": "Password123!"})
    res_auth = client.get("/api/recovery/overview")
    assert res_auth.status_code == 200
    assert "counts" in res_auth.json()


def test_case_detail_authorization_and_scoping():
    client = TestClient(app)
    owner_merchant_id = settings.razorpay_merchant_id

    # Create case for owner merchant (merchant 1)
    db = SessionLocal()
    case = RecoveryCase(merchant_id=owner_merchant_id, status="VERIFYING", recoverable_amount=199.99, currency="USD")
    db.add(case)
    db.commit()
    case_id = case.id
    db.close()

    # Requirement E: Unauthenticated -> 401
    res_unauth = client.get(f"/api/recovery-cases/{case_id}")
    assert res_unauth.status_code == 401

    # Requirement E: Owner Merchant -> 200
    u1_email = f"m1_owner_{uuid.uuid4().hex[:8]}@merchant.com"
    client.post("/api/auth/signup", json={"email": u1_email, "password": "Password123!"})
    res_owner = client.get(f"/api/recovery-cases/{case_id}")
    assert res_owner.status_code == 200
    assert res_owner.json()["case_id"] == case_id

    # Requirement G: Merchant B cannot access Merchant A's case -> 404 (safe denial)
    db = SessionLocal()
    m2 = Merchant(name="Other Merchant Ltd")
    db.add(m2)
    db.commit()
    u2 = User(merchant_id=m2.id, email=f"m2_other_{uuid.uuid4().hex[:8]}@merchant.com", password_hash=hash_password("Password123!"))
    db.add(u2)
    db.commit()
    u2_email = u2.email
    db.close()

    client_m2 = TestClient(app)
    client_m2.post("/api/auth/login", json={"email": u2_email, "password": "Password123!"})
    res_other = client_m2.get(f"/api/recovery-cases/{case_id}")
    assert res_other.status_code == 404


def test_sse_stream_authorization_and_scoping():
    client = TestClient(app)
    owner_merchant_id = settings.razorpay_merchant_id

    db = SessionLocal()
    case = RecoveryCase(merchant_id=owner_merchant_id, status="RECOVERED", recoverable_amount=149.00, currency="USD")
    db.add(case)
    db.commit()
    case_id = case.id
    db.close()

    # Requirement F: Unauthenticated -> 401
    res_unauth = client.get(f"/api/recovery-cases/{case_id}/stream")
    assert res_unauth.status_code == 401

    # Requirement F: Owner merchant stream -> allowed (200)
    u_email = f"sse_owner_{uuid.uuid4().hex[:8]}@merchant.com"
    client.post("/api/auth/signup", json={"email": u_email, "password": "Password123!"})
    res_owner = client.get(f"/api/recovery-cases/{case_id}/stream")
    assert res_owner.status_code == 200

    # Cross-merchant stream -> 404
    db = SessionLocal()
    m2 = Merchant(name="Other Stream Merchant")
    db.add(m2)
    db.commit()
    u2 = User(merchant_id=m2.id, email=f"m2_stream_{uuid.uuid4().hex[:8]}@merchant.com", password_hash=hash_password("Password123!"))
    db.add(u2)
    db.commit()
    u2_email = u2.email
    db.close()

    client_m2 = TestClient(app)
    client_m2.post("/api/auth/login", json={"email": u2_email, "password": "Password123!"})
    res_other_stream = client_m2.get(f"/api/recovery-cases/{case_id}/stream")
    assert res_other_stream.status_code == 404


def test_logout_invalidates_operational_access():
    client = TestClient(app)
    email = f"logout_ops_{uuid.uuid4().hex[:8]}@merchant.com"
    client.post("/api/auth/signup", json={"email": email, "password": "Password123!"})

    # Operational endpoint allowed when logged in
    res_before = client.get("/api/recovery/overview")
    assert res_before.status_code == 200

    # Logout
    client.post("/api/auth/logout")

    # Requirement H: Previously valid session no longer authorizes operational APIs -> 401
    res_after = client.get("/api/recovery/overview")
    assert res_after.status_code == 401


def test_webhook_and_demo_routes_remain_functional():
    client = TestClient(app)
    # Requirement I: Webhook ingestion remains public without browser auth header
    res_wh = client.post("/webhooks/providers/razorpay")
    # Missing payload / signature returns 400 Bad Request or 401 Signature Invalid, NOT 401 "Not authenticated"
    assert res_wh.status_code in (400, 401)
    assert res_wh.json().get("detail") != "Not authenticated"

    # Requirement J: Demo scenario endpoint remains functional
    res_demo = client.post("/api/demo/recovery-scenario")
    assert res_demo.status_code == 200
    assert "case_id" in res_demo.json()
