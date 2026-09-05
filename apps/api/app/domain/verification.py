from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from app.domain.execution import ExecutionResult
from app.domain.decision import DecisionContext


VERIF_STATUS_RECOVERED = "RECOVERED"
VERIF_STATUS_NOT_RECOVERED = "NOT_RECOVERED"
VERIF_STATUS_PENDING = "PENDING"
VERIF_STATUS_FAILED = "FAILED"
VERIF_STATUS_UNKNOWN = "UNKNOWN"


@dataclass
class VerificationResult:
    execution_id: str
    status: str
    verified: bool
    outcome: str
    verified_at: datetime
    provider_reference: Optional[str]
    evidence: Dict[str, Any]
    message: str


def verify_execution(execution: ExecutionResult, context: DecisionContext) -> VerificationResult:
    """
    Deterministic verification of execution outcome using available context.

    - For financial actions, RECOVERED only if revenue_truth.contributing_payments
      includes a captured payment with provider_payment_id matching execution.provider_reference.
    - If provider reported success but no captured evidence yet -> PENDING.
    - For notification actions, verification may confirm provider acceptance but not RECOVERED.
    - Does not mutate DB.
    """
    now = datetime.now(tz=timezone.utc)
    provider_ref = execution.provider_reference
    evidence = dict(execution.evidence or {})

    # default unknown
    status = VERIF_STATUS_UNKNOWN
    verified = False
    outcome = "unknown"
    message = ""

    # Map execution status quick-fail
    if execution.status == "FAILED":
        status = VERIF_STATUS_FAILED
        verified = False
        outcome = "failed"
        message = execution.message or "provider reported failure"
        return VerificationResult(
            execution_id=execution.execution_id,
            status=status,
            verified=verified,
            outcome=outcome,
            verified_at=now,
            provider_reference=provider_ref,
            evidence=evidence,
            message=message,
        )

    # For financial actions, require evidence in revenue_truth
    financial_actions = {"attempt_capture_retry", "offer_discount"}
    contact_actions = {"notify_customer_failure", "send_cart_recovery_email"}

    action = execution.action
    rt = context.revenue_truth

    if action in financial_actions:
        # look for contributing payment matching provider_reference and captured state
        found = False
        for cp in rt.contributing_payments or []:
            if getattr(cp, "provider_payment_id", None) and provider_ref and cp.provider_payment_id == provider_ref:
                if getattr(cp, "provider_state", None) == "captured":
                    found = True
                    break

        if found:
            status = VERIF_STATUS_RECOVERED
            verified = True
            outcome = "recovered"
            message = "financial capture verified in revenue truth"
        else:
            # provider may have accepted execution but capture not yet visible
            if execution.status == "EXECUTED":
                status = VERIF_STATUS_PENDING
                verified = False
                outcome = "pending"
                message = "provider executed but no confirmed capture in revenue truth"
            elif execution.status == "PENDING":
                status = VERIF_STATUS_PENDING
                verified = False
                outcome = "pending"
                message = "provider reports pending"
            else:
                status = VERIF_STATUS_UNKNOWN
                verified = False
                outcome = "unknown"
                message = "no definitive evidence"

        return VerificationResult(
            execution_id=execution.execution_id,
            status=status,
            verified=verified,
            outcome=outcome,
            verified_at=now,
            provider_reference=provider_ref,
            evidence=evidence,
            message=message,
        )

    # For contact/notification actions: verification may confirm provider acceptance
    if action in contact_actions:
        if execution.status == "EXECUTED":
            status = VERIF_STATUS_NOT_RECOVERED
            verified = True
            outcome = "not_recovered"
            message = "notification executed; no financial recovery"
        elif execution.status == "PENDING":
            status = VERIF_STATUS_PENDING
            verified = False
            outcome = "pending"
            message = "provider reports pending for notification"
        else:
            status = VERIF_STATUS_FAILED
            verified = False
            outcome = "failed"
            message = execution.message or "notification failed"

        return VerificationResult(
            execution_id=execution.execution_id,
            status=status,
            verified=verified,
            outcome=outcome,
            verified_at=now,
            provider_reference=provider_ref,
            evidence=evidence,
            message=message,
        )

    # Manual actions: remain pending until human completes
    manual_actions = {"manual_review", "collect_more_evidence", "create_recovery_case"}
    if action in manual_actions:
        status = VERIF_STATUS_PENDING
        verified = False
        outcome = "pending"
        message = "manual action requires human completion"
        return VerificationResult(
            execution_id=execution.execution_id,
            status=status,
            verified=verified,
            outcome=outcome,
            verified_at=now,
            provider_reference=provider_ref,
            evidence=evidence,
            message=message,
        )

    # Fallback unknown
    return VerificationResult(
        execution_id=execution.execution_id,
        status=VERIF_STATUS_UNKNOWN,
        verified=False,
        outcome="unknown",
        verified_at=now,
        provider_reference=provider_ref,
        evidence=evidence,
        message="action type not recognized for verification",
    )
