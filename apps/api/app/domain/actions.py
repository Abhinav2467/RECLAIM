from dataclasses import dataclass
from typing import Dict, Any, List

from app.domain.diagnosis import DiagnosisResult
from app.domain.revenue_truth import RevenueTruthResult
from decimal import Decimal


@dataclass
class ActionCandidate:
    action: str
    eligible: bool
    reason: str
    constraints: Dict[str, Any]


SUPPORTED_ACTIONS: List[str] = [
    "attempt_capture_retry",
    "notify_customer_failure",
    "send_cart_recovery_email",
    "offer_discount",
    "manual_review",
    "collect_more_evidence",
    "create_recovery_case",
]


def _has_authorization_provenance(diagnosis: DiagnosisResult, revenue_truth: RevenueTruthResult | None) -> bool:
    # conservative: require explicit authorization_row_id evidence or a contributing payment with provider_state 'authorized'
    if diagnosis is None:
        return False
    if diagnosis.evidence.get("authorization_row_id"):
        return True
    # inspect revenue truth provenance
    if revenue_truth:
        for cp in revenue_truth.contributing_payments or []:
            if getattr(cp, "provider_state", None) == "authorized":
                return True
    return False


def generate_candidates(diagnosis: DiagnosisResult, revenue_truth: RevenueTruthResult | None) -> List[ActionCandidate]:
    """Generate deterministic, explainable action eligibility candidates.

    - Pure and read-only.
    - Returns an explicit candidate for each SUPPORTED_ACTIONS entry.
    """
    candidates: List[ActionCandidate] = []
    diag = diagnosis.diagnosis if diagnosis else None

    # helper to add with defaults
    def add(action: str, eligible: bool, reason: str, constraints: Dict[str, Any] | None = None):
        candidates.append(ActionCandidate(action=action, eligible=eligible, reason=reason, constraints=constraints or {}))

    # Default: conservative ineligibility
    if diag == "PAYMENT_FAILURE":
        add("notify_customer_failure", True, "Payment marked failed; customer notification appropriate")
        add("create_recovery_case", True, "Failure warrants a recovery case for human follow-up")
        add("manual_review", True, "Payment failed; manual review may find remediation")
        add("collect_more_evidence", True, "Gather logs and provider failure details before aggressive actions")
        # attempt_capture_retry only if explicit authorization provenance exists
        retry_ok = _has_authorization_provenance(diagnosis, revenue_truth)
        add("attempt_capture_retry", retry_ok, "Retry only if explicit authorization/provenance exists", {"requires_authorization_provenance": retry_ok})
        add("send_cart_recovery_email", False, "Not applicable for an already-submitted failed payment")
        add("offer_discount", False, "Discount not appropriate for failed payment without abandonment context")

    elif diag == "AUTHORIZATION_STALE":
        add("attempt_capture_retry", True, "Authorized payment may be retried before it expires")
        add("manual_review", True, "Manual review can confirm retry validity")
        add("create_recovery_case", True, "Create case to coordinate capture retry and tracking")
        add("notify_customer_failure", False, "Authorization stale is not a definite failure; avoid alarming customer")
        add("send_cart_recovery_email", False, "Checkout abandonment flow not applicable")
        add("offer_discount", False, "No evidence of abandonment or discount channel")
        add("collect_more_evidence", True, "Collect provider timestamps and logs before aggressive retry")

    elif diag == "CHECKOUT_ABANDONMENT":
        # send_cart_recovery_email eligible
        add("send_cart_recovery_email", True, "Order appears abandoned; email recovery is appropriate")
        # offer_discount eligible only if revenue_truth indicates recoverable_amount present and > 0
        discount_ok = False
        if revenue_truth and getattr(revenue_truth, "recoverable_amount", None) is not None:
            try:
                if Decimal(revenue_truth.recoverable_amount) > Decimal("0"):
                    discount_ok = True
            except Exception:
                discount_ok = False
        add("offer_discount", discount_ok, "Offer discount only if recoverable amount is known and positive", {"recoverable_amount": str(getattr(revenue_truth, "recoverable_amount", None))})
        add("create_recovery_case", True, "Create case to coordinate cart recovery efforts")
        add("collect_more_evidence", True, "Gather browsing and checkout logs to improve recovery quality")
        add("manual_review", True, "Manual review can inspect abandonment cause and campaign eligibility")
        add("attempt_capture_retry", False, "No authorization exists to retry capture for abandoned cart")
        add("notify_customer_failure", False, "No failure occurred to notify about")

    elif diag == "UNKNOWN":
        add("collect_more_evidence", True, "Unknown diagnosis; collect telemetry and provider logs")
        add("manual_review", True, "Manual investigation required for unknown cases")
        add("create_recovery_case", True, "Escalate unknowns to recovery team for investigation")
        add("attempt_capture_retry", False, "Insufficient evidence to attempt automated capture retry")
        add("notify_customer_failure", False, "Avoid customer notification without clear failure signal")
        add("send_cart_recovery_email", False, "No abandonment signal")
        add("offer_discount", False, "No justification for discounts in unknown cases")

    else:
        # Fallback conservative defaults
        for a in SUPPORTED_ACTIONS:
            add(a, False, "No deterministic eligibility rules matched for this diagnosis")

    return candidates
