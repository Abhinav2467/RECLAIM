from typing import Optional
from app.domain.decision import DecisionContext
from app.domain.execution import RecoveryProviderResult
from app.core.config import settings


class RazorpayRecoveryProvider:
    """Razorpay provider adapter boundary implementing the RecoveryProvider protocol.

    Acts as an explicit stub boundary for live execution until production network calls
    are enabled, ensuring no unexpected network side-effects take place.
    """

    def __init__(self, key_id: Optional[str] = None, key_secret: Optional[str] = None, enabled: bool = False):
        self.key_id = key_id if key_id is not None else getattr(settings, "razorpay_key_id", "")
        self.key_secret = key_secret if key_secret is not None else getattr(settings, "razorpay_key_secret", "")
        self.enabled = enabled

    @property
    def is_configured(self) -> bool:
        return bool(self.key_id and self.key_secret)

    def execute(self, action: str, context: DecisionContext, idempotency_key: str) -> RecoveryProviderResult:
        if action != "attempt_capture_retry":
            return RecoveryProviderResult(
                status="rejected",
                provider_reference=None,
                message=f"Action '{action}' is not supported by Razorpay provider",
                evidence={"provider": "razorpay", "action": action, "supported": False},
            )

        if not self.is_configured:
            return RecoveryProviderResult(
                status="rejected",
                provider_reference=None,
                message="Razorpay API credentials (key_id/key_secret) not configured",
                evidence={"provider": "razorpay", "action": action, "configured": False},
            )

        if not self.enabled:
            return RecoveryProviderResult(
                status="rejected",
                provider_reference=None,
                message="Razorpay live network execution is explicitly disabled in adapter stub",
                evidence={"provider": "razorpay", "action": action, "configured": True, "live_network_enabled": False},
            )

        return RecoveryProviderResult(
            status="failed",
            provider_reference=None,
            message="Razorpay live API transport not implemented",
            evidence={"provider": "razorpay", "action": action},
        )
