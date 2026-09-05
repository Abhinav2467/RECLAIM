from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from app.domain.revenue_truth import RevenueTruthResult
from app.domain.diagnosis import DiagnosisResult
from app.domain.actions import ActionCandidate
from app.domain.economics import EconomicEvaluation


class DecisionValidationError(Exception):
    pass


ALLOWED_DECISIONS = ("RECOMMEND_ACTION", "NO_ACTION", "NEEDS_REVIEW")


def _require_tz(dt: datetime):
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise DecisionValidationError("timestamp must be timezone-aware")


@dataclass(frozen=True)
class DecisionContext:
    context_version: int
    generated_at: datetime
    revenue_truth: RevenueTruthResult
    diagnosis: DiagnosisResult
    action_candidates: List[ActionCandidate]
    economic_evaluations: List[EconomicEvaluation]
    case_id: Optional[int] = field(default=None)
    component_versions: Dict[str, str] = field(default_factory=dict)
    evidence: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.context_version, int) or self.context_version <= 0:
            raise DecisionValidationError("context_version must be a positive integer")
        _require_tz(self.generated_at)
        # populate case_id from revenue_truth if not provided
        if self.case_id is None and hasattr(self.revenue_truth, "order_id"):
            object.__setattr__(self, "case_id", getattr(self.revenue_truth, "order_id"))


@dataclass(frozen=True)
class DecisionResult:
    decision: str
    recommended_action: Optional[str]
    context_version: int
    decided_at: datetime
    rationale: str
    evidence: Dict[str, Any]
    agent_version: str
    confidence: str

    def __post_init__(self):
        if self.decision not in ALLOWED_DECISIONS:
            raise DecisionValidationError(f"invalid decision value: {self.decision}")
        if not isinstance(self.context_version, int) or self.context_version <= 0:
            raise DecisionValidationError("context_version must be a positive integer")
        _require_tz(self.decided_at)
        # decision-specific requirements
        if self.decision == "RECOMMEND_ACTION":
            if not self.recommended_action:
                raise DecisionValidationError("RECOMMEND_ACTION requires a recommended_action")
        else:
            # NO_ACTION and NEEDS_REVIEW must not carry recommended_action
            if self.recommended_action is not None:
                raise DecisionValidationError(f"{self.decision} must not include a recommended_action")


def validate_decision_context(current_context_version: int, decision_result: DecisionResult) -> bool:
    """Validate that the decision_result applies to the current context version.

    Raises DecisionValidationError if stale or invalid.
    Returns True when valid.
    """
    if not isinstance(current_context_version, int) or current_context_version <= 0:
        raise DecisionValidationError("current_context_version must be a positive integer")
    if decision_result.context_version != current_context_version:
        raise DecisionValidationError("stale decision: context version mismatch")
    return True


def validate_decision_against_context(decision_result: DecisionResult, context: DecisionContext) -> bool:
    """Additional validation that recommended_action (if present) matches an eligible candidate in context.

    Raises DecisionValidationError for violations. Returns True if valid.
    """
    # first validate version
    validate_decision_context(context.context_version, decision_result)

    if decision_result.decision == "RECOMMEND_ACTION":
        # ensure recommended_action exists in action_candidates and is eligible
        ra = decision_result.recommended_action
        matches = [c for c in context.action_candidates if c.action == ra]
        if not matches:
            raise DecisionValidationError("recommended_action not found in context action_candidates")
        if not matches[0].eligible:
            raise DecisionValidationError("recommended_action is explicitly ineligible")

    # NO_ACTION and NEEDS_REVIEW impose no further cross-checks here
    return True
