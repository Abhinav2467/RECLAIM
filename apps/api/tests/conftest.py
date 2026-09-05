import json
import hmac
import hashlib
import pytest

from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.db.session import SessionLocal, engine, Base
from sqlalchemy import text
from app.db.models import Merchant, User, RawWebhookEvent
from app.core.security import hash_password


@pytest.fixture(autouse=True)
def db_session():
    """Provide a clean DB state for each test: ensure merchant id=1 and default test operator exist."""
    db = SessionLocal()
    try:
        # Ensure configured test secret and merchant id are set for deterministic tests
        settings.razorpay_webhook_secret = getattr(settings, "razorpay_webhook_secret", "testsecret")
        settings.razorpay_merchant_id = getattr(settings, "razorpay_merchant_id", 1)

        # Clean users and raw_webhook_events
        db.execute(text("DELETE FROM users"))
        db.execute(text("DELETE FROM raw_webhook_events"))
        db.execute(text("DELETE FROM merchants WHERE id = 1"))
        db.commit()

        # Insert merchant id=1
        m = Merchant(id=1, name="RECLAIM Demo Merchant", metadata_json={"environment": "development"})
        db.add(m)
        db.commit()

        # Insert default test user for merchant id=1
        u = User(
            merchant_id=1,
            email="test_operator@reclaim.local",
            password_hash=hash_password("TestPassword123!"),
            is_active=True,
        )
        db.add(u)
        db.commit()

        yield db
    finally:
        db.close()


@pytest.fixture
def client(db_session):
    """Provide an authenticated TestClient instance for merchant id=1."""
    c = TestClient(app)
    c.post("/api/auth/login", json={"email": "test_operator@reclaim.local", "password": "TestPassword123!"})
    return c


def make_signature(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


@pytest.fixture
def sign():
    # Use the application's configured webhook secret so tests mirror runtime
    return lambda body: make_signature(settings.razorpay_webhook_secret, body)
