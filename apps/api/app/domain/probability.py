from dataclasses import dataclass
from decimal import Decimal, getcontext
from typing import Dict, Any
import datetime

from app.domain.revenue_truth import RevenueTruthResult
from app.domain.diagnosis import DiagnosisResult

# ensure sufficient Decimal precision
getcontext().prec = 6


@dataclass
class ProbabilityEstimate:
    action: str
    probability: Decimal  # in [0,1]
    confidence: str       # 'high'|'medium'|'low'
    evidence: Dict[str, Any]
    model_version: str


def _clip(p: Decimal) -> Decimal:
    if p < Decimal("0"):
        return Decimal("0")
    if p > Decimal("1"):
        return Decimal("1")
    return p


def estimate(
    diagnosis: DiagnosisResult,
    revenue_truth: RevenueTruthResult | None,
    action: str,
    now: datetime.datetime | None = None,
) -> ProbabilityEstimate:
    """Deterministic, read-only probability estimator for recovery actions.

    Inputs: `diagnosis` (required), `revenue_truth` (may be None), action string.
    Returns ProbabilityEstimate with Decimal probability in [0,1].
    """
    if now is None:
        now = datetime.datetime.now(tz=datetime.timezone.utc)

    dv = diagnosis.diagnosis if diagnosis else None
    conf = diagnosis.confidence if diagnosis else "low"
    evidence: Dict[str, Any] = {"diagnosis": dv, "diagnosis_confidence": conf}
    if revenue_truth is not None:
        evidence["revenue_truth_resolution"] = revenue_truth.resolution
        evidence["captured_amount"] = str(revenue_truth.captured_amount)
        evidence["expected_amount"] = str(revenue_truth.expected_amount) if revenue_truth.expected_amount is not None else None

    # base probabilities per action and diagnosis
    base = Decimal("0.05")
    # action-specific base adjustments
    if action == "notify_customer_failure":
        if dv == "PAYMENT_FAILURE":
            base = Decimal("0.6")
        elif dv == "UNKNOWN":
            base = Decimal("0.15")
    elif action == "attempt_capture_retry":
        if dv == "AUTHORIZATION_STALE":
            base = Decimal("0.45")
        elif dv == "PAYMENT_FAILURE":
            base = Decimal("0.1")
    elif action == "send_cart_recovery_email":
        if dv == "CHECKOUT_ABANDONMENT":
            base = Decimal("0.4")
        else:
            base = Decimal("0.05")
    elif action == "manual_review":
        if dv == "UNKNOWN":
            base = Decimal("0.6")
        else:
            base = Decimal("0.15")
    elif action == "collect_more_evidence":
        if dv == "UNKNOWN":
            base = Decimal("0.5")
        else:
            base = Decimal("0.1")

    # modifiers from confidence
    mod = Decimal("0")
    if conf == "high":
        mod += Decimal("0.15")
    elif conf == "medium":
        mod += Decimal("0.05")
    else:
        mod += Decimal("0")

    # revenue_truth presence increases confidence for capture retry decisions
    if revenue_truth is not None:
        if action == "attempt_capture_retry":
            # if no captured_amount and expected_amount known -> slightly higher
            if revenue_truth.expected_amount is not None and revenue_truth.captured_amount == Decimal("0"):
                mod += Decimal("0.1")

    # evidence-based tweaks: presence of provider_event_id/provenance
    prov = diagnosis.evidence.get("provider_event_id") or diagnosis.evidence.get("payment.provider_event_id")
    if prov:
        # provenance increases probability modestly for customer-facing actions
        if action in ("notify_customer_failure", "attempt_capture_retry"):
            mod += Decimal("0.05")

    # age-based penalty for very old authorizations (if present)
    auth_age = diagnosis.evidence.get("authorization_age_seconds")
    if auth_age is not None and action == "attempt_capture_retry":
        # older than an hour reduces success probability
        if auth_age > 3600:
            mod -= Decimal("0.1")

    prob = _clip(base + mod)

    # map net confidence string
    net_conf = conf
    if prob >= Decimal("0.75"):
        net_conf = "high"
    elif prob >= Decimal("0.35"):
        net_conf = "medium"
    else:
        net_conf = "low"

    pe = ProbabilityEstimate(
        action=action,
        probability=prob,
        confidence=net_conf,
        evidence=evidence,
        model_version="deterministic-v1",
    )

    return pe
