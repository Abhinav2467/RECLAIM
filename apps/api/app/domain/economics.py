from dataclasses import dataclass
from decimal import Decimal, getcontext
from typing import Optional, Dict, Any, List

from app.domain.actions import ActionCandidate
from app.domain.probability import ProbabilityEstimate
from app.domain.revenue_truth import RevenueTruthResult

# ensure Decimal precision
getcontext().prec = 12


@dataclass
class EconomicEvaluation:
    action: str
    eligible: bool
    recoverable_amount: Optional[Decimal]
    success_probability: Decimal
    expected_recovered_amount: Optional[Decimal]
    intervention_cost: Decimal
    expected_net_recovery: Optional[Decimal]
    currency: Optional[str]
    economically_viable: bool
    reason: str
    evidence: Dict[str, Any]


def _clip_probability(p: Decimal) -> Decimal:
    if p is None:
        raise ValueError("probability must be provided as Decimal")
    if p < Decimal("0"):
        return Decimal("0")
    if p > Decimal("1"):
        return Decimal("1")
    return p


def evaluate(
    candidate: ActionCandidate,
    probability: ProbabilityEstimate,
    revenue_truth: RevenueTruthResult | None,
    intervention_costs: Dict[str, Decimal],
) -> EconomicEvaluation:
    """Evaluate economic expectation for a single candidate.

    - Uses only provided inputs; pure and deterministic.
    - intervention_costs must contain an entry for candidate.action.
    """
    action = candidate.action
    eligible = bool(candidate.eligible)

    # intervention cost must be explicit
    if action not in intervention_costs:
        raise KeyError(f"intervention cost missing for action: {action}")
    cost = intervention_costs[action]
    if not isinstance(cost, Decimal):
        raise TypeError("intervention_costs values must be Decimal")

    # start building evidence
    evidence: Dict[str, Any] = {
        "candidate_reason": candidate.reason,
        "candidate_constraints": candidate.constraints,
        "probability_confidence": probability.confidence,
        "probability_model_version": probability.model_version,
    }

    # validate and clamp probability
    prob = _clip_probability(probability.probability)

    # default outputs
    recoverable = None
    expected_recovered = None
    expected_net = None
    currency = None
    economically_viable = False
    reason = ""

    if not eligible:
        reason = "Action not eligible"
        return EconomicEvaluation(
            action=action,
            eligible=False,
            recoverable_amount=None,
            success_probability=prob,
            expected_recovered_amount=None,
            intervention_cost=cost,
            expected_net_recovery=None,
            currency=None,
            economically_viable=False,
            reason=reason,
            evidence=evidence,
        )

    # when eligible, pull recoverable amount and currency from revenue_truth
    if revenue_truth is None:
        reason = "Missing revenue truth; cannot compute recoverable amount"
        return EconomicEvaluation(
            action=action,
            eligible=True,
            recoverable_amount=None,
            success_probability=prob,
            expected_recovered_amount=None,
            intervention_cost=cost,
            expected_net_recovery=None,
            currency=None,
            economically_viable=False,
            reason=reason,
            evidence=evidence,
        )

    recoverable = revenue_truth.recoverable_amount
    currency = revenue_truth.currency
    evidence["revenue_truth_resolution"] = revenue_truth.resolution

    if recoverable is None:
        reason = "Recoverable amount unknown"
        return EconomicEvaluation(
            action=action,
            eligible=True,
            recoverable_amount=None,
            success_probability=prob,
            expected_recovered_amount=None,
            intervention_cost=cost,
            expected_net_recovery=None,
            currency=currency,
            economically_viable=False,
            reason=reason,
            evidence=evidence,
        )

    # ensure Decimal type for recoverable
    if not isinstance(recoverable, Decimal):
        try:
            recoverable = Decimal(recoverable)
        except Exception:
            reason = "Invalid recoverable amount type"
            return EconomicEvaluation(
                action=action,
                eligible=True,
                recoverable_amount=None,
                success_probability=prob,
                expected_recovered_amount=None,
                intervention_cost=cost,
                expected_net_recovery=None,
                currency=currency,
                economically_viable=False,
                reason=reason,
                evidence=evidence,
            )

    # Now compute expected recovered amount
    expected_recovered = (recoverable * prob).quantize(Decimal("0.01"))
    expected_net = (expected_recovered - cost).quantize(Decimal("0.01"))

    # currency must be present to be economically viable
    if currency is None:
        reason = "Currency unknown; cannot determine economic viability"
        economically_viable = False
    else:
        if expected_net > Decimal("0"):
            economically_viable = True
            reason = "Expected net recovery positive"
        else:
            economically_viable = False
            reason = "Expected recovery does not exceed intervention cost"

    return EconomicEvaluation(
        action=action,
        eligible=True,
        recoverable_amount=recoverable,
        success_probability=prob,
        expected_recovered_amount=expected_recovered,
        intervention_cost=cost,
        expected_net_recovery=expected_net,
        currency=currency,
        economically_viable=economically_viable,
        reason=reason,
        evidence=evidence,
    )


def evaluate_batch(
    candidates: List[ActionCandidate],
    probabilities: Dict[str, ProbabilityEstimate],
    revenue_truth: RevenueTruthResult | None,
    intervention_costs: Dict[str, Decimal],
) -> List[EconomicEvaluation]:
    results: List[EconomicEvaluation] = []
    for c in candidates:
        pe = probabilities.get(c.action)
        if pe is None:
            raise KeyError(f"missing probability for action {c.action}")
        results.append(evaluate(c, pe, revenue_truth, intervention_costs))
    return results
