import hmac
import hashlib
from typing import Optional


def verify_signature(secret: str, body: bytes, signature_header: Optional[str]) -> bool:
    """Verify Razorpay webhook signature.

    Per Razorpay docs, the signature is an HMAC SHA256 hex digest computed using
    the webhook secret as the key and the raw request body as the message.
    This function computes the expected hex digest and uses a constant-time
    comparison to verify the header.
    """
    if not signature_header:
        return False
    try:
        # Compute HMAC-SHA256 hex digest
        expected = hmac.new(secret.encode('utf-8'), body, hashlib.sha256).hexdigest()
    except Exception:
        return False
    # header may contain the signature directly
    received = signature_header.strip()
    return hmac.compare_digest(expected, received)
