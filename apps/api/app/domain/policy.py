from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any, Set

from app.domain.decision import DecisionContext, DecisionResult, DecisionValidationError, validate_decision_context
from app.domain.actions import ActionCandidate


PolicyMode = str  # 'OBSERVE'|'RECOMMEND'|'AUTONOMOUS'


CONTACT_ACTIONS: Set[str] = {"notify_customer_failure", "send_cart_recovery_email"}
FINANCIAL_ACTIONS: Set[str] = {"attempt_capture_retry", "offer_discount"}


@dataclass
class PolicyDecision:
    decision: str  # APPROVED|BLOCKED|NO_ACTION|NEEDS_REVIEW
    action: Optional[str]
    approved: bool
    reasons: List[str]
    constraints: Dict[str, Any]
    evaluated_at: datetime
    policy_version: str = "policy-v1"


@dataclass
class PolicyContext:
    decision_context: DecisionContext
    decision_result: DecisionResult
    merchant_kill_switch: bool = False
    mode: PolicyMode = "OBSERVE"
    remaining_budget: Optional[Decimal] = None
    contact_count: int = 0
    max_contacts: int = 3
    policy_inputs: Dict[str, Any] = None


def evaluate_policy(ctx: PolicyContext) -> PolicyDecision:
    now = datetime.now(tz=timezone.utc)
    dr = ctx.decision_result

    # Stale context validation
    try:
        validate_decision_context(ctx.decision_context.context_version, dr)
    except DecisionValidationError as e:
        return PolicyDecision(decision="BLOCKED", action=dr.recommended_action, approved=False, reasons=["stale_context", str(e)], constraints={}, evaluated_at=now)

    # NO_ACTION and NEEDS_REVIEW pass through
    if dr.decision == "NO_ACTION":
        return PolicyDecision(decision="NO_ACTION", action=None, approved=False, reasons=["no_action"], constraints={}, evaluated_at=now)
    if dr.decision == "NEEDS_REVIEW":
        return PolicyDecision(decision="NEEDS_REVIEW", action=None, approved=False, reasons=["needs_review"], constraints={}, evaluated_at=now)

    # Now handle RECOMMEND_ACTION
    if dr.decision != "RECOMMEND_ACTION":
        return PolicyDecision(decision="BLOCKED", action=dr.recommended_action, approved=False, reasons=["invalid_decision_type"], constraints={}, evaluated_at=now)

    action = dr.recommended_action
    reasons: List[str] = []
    constraints: Dict[str, Any] = {}

    # must exist among action_candidates and be eligible
    matches = [c for c in ctx.decision_context.action_candidates if c.action == action]
    if not matches:
        reasons.append("missing_candidate")
        return PolicyDecision(decision="BLOCKED", action=action, approved=False, reasons=reasons, constraints=constraints, evaluated_at=now)
    candidate: ActionCandidate = matches[0]
    if not candidate.eligible:
        reasons.append("candidate_ineligible")
        return PolicyDecision(decision="BLOCKED", action=action, approved=False, reasons=reasons, constraints=constraints, evaluated_at=now)

    # Shadow mode: OBSERVE/RECOMMEND block autonomous approval
    if ctx.mode in ("OBSERVE", "RECOMMEND"):
        reasons.append(f"mode_{ctx.mode.lower()}")
        return PolicyDecision(decision="BLOCKED", action=action, approved=False, reasons=reasons, constraints=constraints, evaluated_at=now)

    # Merchant kill switch blocks autonomous recovery actions
    if ctx.merchant_kill_switch:
        reasons.append("merchant_kill_switch_enabled")
        return PolicyDecision(decision="BLOCKED", action=action, approved=False, reasons=reasons, constraints=constraints, evaluated_at=now)

    # Contact fatigue
    if action in CONTACT_ACTIONS:
        if ctx.contact_count >= ctx.max_contacts:
            reasons.append("contact_fatigue")
            constraints["contact_count"] = ctx.contact_count
            constraints["max_contacts"] = ctx.max_contacts
            return PolicyDecision(decision="BLOCKED", action=action, approved=False, reasons=reasons, constraints=constraints, evaluated_at=now)

    # Recovery budget checks for financial actions
    if action in FINANCIAL_ACTIONS:
        # recoverable_amount from revenue truth
        recoverable = ctx.decision_context.revenue_truth.recoverable_amount
        if recoverable is None:
            reasons.append("unknown_recoverable_amount")
            return PolicyDecision(decision="BLOCKED", action=action, approved=False, reasons=reasons, constraints=constraints, evaluated_at=now)
        # ensure Decimal
        if not isinstance(recoverable, Decimal):
            try:
                recoverable = Decimal(recoverable)
            except Exception:
                reasons.append("invalid_recoverable_amount")
                return PolicyDecision(decision="BLOCKED", action=action, approved=False, reasons=reasons, constraints=constraints, evaluated_at=now)
        if ctx.remaining_budget is None:
            reasons.append("no_budget_info")
            return PolicyDecision(decision="BLOCKED", action=action, approved=False, reasons=reasons, constraints=constraints, evaluated_at=now)
        if recoverable > ctx.remaining_budget:
            reasons.append("insufficient_budget")
            constraints["recoverable_amount"] = str(recoverable)
            constraints["remaining_budget"] = str(ctx.remaining_budget)
            return PolicyDecision(decision="BLOCKED", action=action, approved=False, reasons=reasons, constraints=constraints, evaluated_at=now)

    # Passed all checks -> APPROVED
    reasons.append("policy_checks_passed")
    return PolicyDecision(decision="APPROVED", action=action, approved=True, reasons=reasons, constraints=constraints, evaluated_at=now)
