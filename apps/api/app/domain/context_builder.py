from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Dict, List

from sqlalchemy.orm import Session

from app.domain.revenue_truth import assess_order_revenue, RevenueTruthResult
from app.domain.diagnosis import diagnose, DiagnosisResult
from app.domain.actions import generate_candidates, ActionCandidate, SUPPORTED_ACTIONS
from app.domain.probability import estimate, ProbabilityEstimate
from app.domain.economics import evaluate_batch, EconomicEvaluation
from app.domain.decision import DecisionContext

DEFAULT_INTERVENTION_COSTS: Dict[str, Decimal] = {
    "attempt_capture_retry": Decimal("0.50"),
    "notify_customer_failure": Decimal("0.10"),
    "send_cart_recovery_email": Decimal("0.05"),
    "offer_discount": Decimal("2.00"),
    "manual_review": Decimal("5.00"),
    "collect_more_evidence": Decimal("0.00"),
    "create_recovery_case": Decimal("0.00"),
}


def build_decision_context(
    db: Session,
    order_id: Optional[int] = None,
    payment_id: Optional[int] = None,
    case_id: Optional[int] = None,
    context_version: int = 1,
    intervention_costs: Optional[Dict[str, Decimal]] = None,
) -> DecisionContext:
    """Deterministic, read-only context builder constructing a DecisionContext from PostgreSQL.

    - Calls assess_order_revenue to compute authoritative revenue truth.
    - Calls diagnose to analyze failure/state.
    - Calls generate_candidates to produce action candidates.
    - Calls estimate for action probability estimates.
    - Calls evaluate_batch for economic evaluations.
    - Does not mutate DB.
    - Uses timezone-aware UTC timestamps.
    """
    now = datetime.now(tz=timezone.utc)

    # 1. Revenue Truth
    revenue_truth = assess_order_revenue(db, order_id)

    # 2. Diagnosis
    diagnosis = diagnose(db, revenue_truth, order_id=order_id, payment_id=payment_id)

    # 3. Action Candidates
    candidates = generate_candidates(diagnosis, revenue_truth)

    # 4. Probability Estimates
    probabilities: Dict[str, ProbabilityEstimate] = {}
    for candidate in candidates:
        probabilities[candidate.action] = estimate(diagnosis, revenue_truth, candidate.action, now=now)

    # 5. Economic Evaluations
    costs = dict(DEFAULT_INTERVENTION_COSTS)
    if intervention_costs:
        costs.update(intervention_costs)

    economic_evaluations = evaluate_batch(candidates, probabilities, revenue_truth, costs)

    # 6. Construct DecisionContext
    return DecisionContext(
        context_version=context_version,
        generated_at=now,
        revenue_truth=revenue_truth,
        diagnosis=diagnosis,
        action_candidates=candidates,
        economic_evaluations=economic_evaluations,
        case_id=case_id,
        component_versions={
            "revenue_truth": "v1",
            "diagnosis": "v1",
            "actions": "v1",
            "probability": "v1",
            "economics": "v1",
        },
    )
