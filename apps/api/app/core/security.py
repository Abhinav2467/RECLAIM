import os
import hashlib
import hmac
import uuid
from typing import Optional

# Secret key for session token signing
SECRET_KEY = os.environ.get("SECRET_KEY", "reclaim-secret-session-key-2026")

def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with 100,000 iterations."""
    salt = os.urandom(16)
    pw_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return f"{salt.hex()}${pw_hash.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify password against PBKDF2-HMAC-SHA256 hash."""
    try:
        salt_hex, hash_hex = stored_hash.split('$')
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)
        actual_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return hmac.compare_digest(actual_hash, expected_hash)
    except Exception:
        return False

def generate_session_token(user_id: int) -> str:
    """Generate a signed session token."""
    nonce = uuid.uuid4().hex
    msg = f"{user_id}:{nonce}".encode('utf-8')
    sig = hmac.new(SECRET_KEY.encode('utf-8'), msg, hashlib.sha256).hexdigest()
    return f"{user_id}:{nonce}:{sig}"

def verify_session_token(token: str) -> Optional[int]:
    """Verify session token signature and return user_id if valid."""
    try:
        parts = token.split(':')
        if len(parts) != 3:
            return None
        user_id_str, nonce, sig = parts
        user_id = int(user_id_str)
        msg = f"{user_id}:{nonce}".encode('utf-8')
        expected_sig = hmac.new(SECRET_KEY.encode('utf-8'), msg, hashlib.sha256).hexdigest()
        if hmac.compare_digest(sig, expected_sig):
            return user_id
        return None
    except Exception:
        return None
