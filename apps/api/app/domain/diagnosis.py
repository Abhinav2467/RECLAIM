from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import datetime

from app.domain.revenue_truth import RevenueTruthResult
from app.db.models import Payment, Order


@dataclass
class DiagnosisResult:
    diagnosis: str
    confidence: str
    order_id: Optional[int]
    payment_ids: List[int]
    evidence: Dict[str, Any]
    suggested_actions: List[str]
    diagnosis_timestamp: datetime.datetime
    notes: Optional[str] = None


def diagnose(
    db,
    revenue_truth: RevenueTruthResult,
    order_id: Optional[int] = None,
    payment_id: Optional[int] = None,
    auth_stale_after: datetime.timedelta = datetime.timedelta(minutes=30),
    abandonment_after: datetime.timedelta = datetime.timedelta(days=1),
) -> DiagnosisResult:
    """Deterministic, read-only diagnosis based on revenue truth and DB state.

    - Does not mutate DB.
    - Uses timezone-aware now in UTC.
    """
    now = datetime.datetime.now(tz=datetime.timezone.utc)

    # Prepare basic context
    pid_list: List[int] = []
    evidence: Dict[str, Any] = {}

    # If payment id provided, inspect payment row deterministically
    payment_row = None
    if payment_id is not None:
        payment_row = db.get(Payment, payment_id)
        if payment_row:
            pid_list.append(payment_row.id)
            evidence["payment.provider_state"] = payment_row.provider_state
            evidence["payment.provider_event_id"] = payment_row.provider_event_id
            evidence["payment.provider_state_at"] = payment_row.provider_state_at
            # include failure details when present
            if hasattr(payment_row, "provider_failure_code"):
                evidence["payment.provider_failure_code"] = getattr(payment_row, "provider_failure_code")
                evidence["provider_failure_code"] = getattr(payment_row, "provider_failure_code")
            if hasattr(payment_row, "provider_failure_reason"):
                evidence["payment.provider_failure_reason"] = getattr(payment_row, "provider_failure_reason")
                evidence["provider_failure_reason"] = getattr(payment_row, "provider_failure_reason")
            # also set top-level provenance keys for easier assertions
            evidence["provider_event_id"] = payment_row.provider_event_id
            evidence["provider_state"] = payment_row.provider_state
            evidence["provider_state_at"] = payment_row.provider_state_at

    # Also gather payments referenced in revenue_truth contributing_payments
    if revenue_truth:
        for cp in revenue_truth.contributing_payments or []:
            if cp.payment_id is not None and cp.payment_id not in pid_list:
                pid_list.append(cp.payment_id)
                # add provenance fields from revenue_truth
                evidence.setdefault("contributing_payments", []).append({
                    "payment_id": cp.payment_id,
                    "provider_payment_id": cp.provider_payment_id,
                    "amount": cp.amount,
                    "currency": cp.currency,
                    "provider_state": cp.provider_state,
                    "provider_event_id": cp.provider_event_id,
                    "provider_state_at": cp.provider_state_at,
                })

    # Diagnosis 1: PAYMENT_FAILURE
    # Rule: Payment.provider_state == 'failed'
    if payment_row is not None and payment_row.provider_state == "failed":
        high_conf = bool(payment_row.provider_event_id and payment_row.provider_state_at)
        confidence = "high" if high_conf else "medium"
        suggested = ["notify_customer_failure", "offer_retry_capture", "create_recovery_case", "manual_review"]
        return DiagnosisResult(
            diagnosis="PAYMENT_FAILURE",
            confidence=confidence,
            order_id=payment_row.order_id,
            payment_ids=[payment_row.id],
            evidence=evidence,
            suggested_actions=suggested,
            diagnosis_timestamp=now,
            notes=None,
        )

    # Diagnosis 2: AUTHORIZATION_STALE
    # Look for an authorized payment with provider_state_at older than auth_stale_after
    # Check payments in pid_list first, then query if order_id provided
    def find_authorized_rows() -> List[Payment]:
        rows: List[Payment] = []
        for pid in pid_list:
            r = db.get(Payment, pid)
            if r and r.provider_state == "authorized":
                rows.append(r)
        if rows:
            return rows
        # if none found in pid_list, search by payment_id param
        if payment_id is not None:
            r = db.get(Payment, payment_id)
            if r and r.provider_state == "authorized":
                return [r]
        # if order_id provided, search all linked payments
        if order_id is not None:
            q = db.query(Payment).filter(Payment.order_id == order_id).all()
            return [r for r in q if r.provider_state == "authorized"]
        return []

    auth_rows = find_authorized_rows()
    for ar in auth_rows:
        if ar.provider_state_at is None:
            continue
        age = now - ar.provider_state_at
        if age > auth_stale_after:
            # Ensure payment not captured
            captured = False
            if ar.provider_state == "captured":
                captured = True
            if not captured:
                confidence = "high" if (ar.provider_event_id and ar.provider_state_at) else "medium"
                suggested = ["attempt_capture_retry", "notify_merchant", "create_recovery_case", "manual_review"]
                evidence.update({"authorization_row_id": ar.id, "authorization_age_seconds": int(age.total_seconds())})
                return DiagnosisResult(
                    diagnosis="AUTHORIZATION_STALE",
                    confidence=confidence,
                    order_id=ar.order_id,
                    payment_ids=[ar.id],
                    evidence=evidence,
                    suggested_actions=suggested,
                    diagnosis_timestamp=now,
                )

    # Diagnosis 3: CHECKOUT_ABANDONMENT
    if order_id is not None:
        order = db.get(Order, order_id)
        if order is not None:
            age = now - order.created_at
            if age > abandonment_after:
                # check no linked payment with provider_state in {'authorized','captured'}
                linked = db.query(Payment).filter(Payment.order_id == order.id).all()
                has_activity = any((p.provider_state in ("authorized", "captured")) for p in linked)
                if not has_activity:
                    suggested = ["send_cart_recovery_email", "offer_discount", "create_recovery_case"]
                    evidence.update({"order_created_at": order.created_at, "order_age_seconds": int(age.total_seconds())})
                    return DiagnosisResult(
                        diagnosis="CHECKOUT_ABANDONMENT",
                        confidence="medium",
                        order_id=order.id,
                        payment_ids=[p.id for p in linked],
                        evidence=evidence,
                        suggested_actions=suggested,
                        diagnosis_timestamp=now,
                    )

    # Diagnosis 4: UNKNOWN
    # If revenue_truth indicates unknown/currency_mismatch/no_order or no other rule matched
    if revenue_truth is None or revenue_truth.resolution in ("unknown", "currency_mismatch", "no_order"):
        suggested = ["manual_investigation", "collect_more_evidence", "escalate"]
        return DiagnosisResult(
            diagnosis="UNKNOWN",
            confidence="low",
            order_id=order_id,
            payment_ids=pid_list,
            evidence=evidence,
            suggested_actions=suggested,
            diagnosis_timestamp=now,
            notes=f"revenue_truth_resolution={getattr(revenue_truth, 'resolution', None)}",
        )

    # Default fallback: UNKNOWN
    return DiagnosisResult(
        diagnosis="UNKNOWN",
        confidence="low",
        order_id=order_id,
        payment_ids=pid_list,
        evidence=evidence,
        suggested_actions=["manual_investigation"],
        diagnosis_timestamp=now,
    )
