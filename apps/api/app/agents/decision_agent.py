from typing import List, Optional
from datetime import datetime, timezone
from decimal import Decimal
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END

from app.domain.decision import (
    DecisionContext,
    DecisionResult,
    validate_decision_against_context,
    validate_decision_context,
    DecisionValidationError,
)


AGENT_VERSION = "deterministic-langgraph-v1"


class _DecisionState(TypedDict):
    context: DecisionContext
    decision_result: Optional[DecisionResult]


def _validate_context_node(state: _DecisionState) -> _DecisionState:
    ctx: DecisionContext = state["context"]
    # Validate context invariants using existing helper
    validate_decision_context(ctx.context_version, DecisionResult(
        decision="NO_ACTION",
        recommended_action=None,
        context_version=ctx.context_version,
        decided_at=datetime.now(tz=timezone.utc),
        rationale="validation",
        evidence={},
        agent_version=AGENT_VERSION,
        confidence=ctx.diagnosis.confidence,
    ))
    return state


def _reason_node(state: _DecisionState) -> _DecisionState:
    ctx: DecisionContext = state["context"]

    viable = [e for e in ctx.economic_evaluations if e.eligible and e.economically_viable and e.expected_net_recovery is not None]

    if not viable:
        state["decision_result"] = DecisionResult(
            decision="NO_ACTION",
            recommended_action=None,
            context_version=ctx.context_version,
            decided_at=datetime.now(tz=timezone.utc),
            rationale="No economically viable eligible actions",
            evidence={"viable_count": 0},
            agent_version=AGENT_VERSION,
            confidence=ctx.diagnosis.confidence,
        )
        return state

    viable_sorted = sorted(viable, key=lambda e: (e.expected_net_recovery, e.action), reverse=True)
    top = viable_sorted[0]

    prob_conf = top.evidence.get("probability_confidence") if isinstance(top.evidence, dict) else None
    diag_conf = ctx.diagnosis.confidence

    needs_review = False
    if prob_conf == "low" or diag_conf == "low":
        needs_review = True

    if needs_review:
        state["decision_result"] = DecisionResult(
            decision="NEEDS_REVIEW",
            recommended_action=None,
            context_version=ctx.context_version,
            decided_at=datetime.now(tz=timezone.utc),
            rationale=f"Top action {top.action} requires review due to low confidence",
            evidence={"top_action": top.action, "expected_net_recovery": str(top.expected_net_recovery)},
            agent_version=AGENT_VERSION,
            confidence="low",
        )
        return state

    state["decision_result"] = DecisionResult(
        decision="RECOMMEND_ACTION",
        recommended_action=top.action,
        context_version=ctx.context_version,
        decided_at=datetime.now(tz=timezone.utc),
        rationale=f"Recommended {top.action} because expected net recovery is {top.expected_net_recovery} {top.currency}",
        evidence={"top_action": top.action, "expected_net_recovery": str(top.expected_net_recovery)},
        agent_version=AGENT_VERSION,
        confidence=ctx.diagnosis.confidence,
    )
    return state


def _validate_recommendation_node(state: _DecisionState) -> _DecisionState:
    ctx: DecisionContext = state["context"]
    dr: DecisionResult = state["decision_result"]
    validate_decision_against_context(dr, ctx)
    return state


# Build and compile the LangGraph StateGraph at module import so it's reused
_builder = StateGraph(_DecisionState)
_builder.add_node(_validate_context_node)
_builder.add_edge(START, _validate_context_node.__name__)
_builder.add_node(_reason_node)
_builder.add_edge(_validate_context_node.__name__, _reason_node.__name__)
_builder.add_node(_validate_recommendation_node)
_builder.add_edge(_reason_node.__name__, _validate_recommendation_node.__name__)
_builder.set_finish_point(_validate_recommendation_node.__name__)
_compiled_graph = _builder.compile()


def run_decision_agent(context: DecisionContext) -> DecisionResult:
    """Invoke the compiled LangGraph StateGraph with the provided DecisionContext.

    Returns the produced DecisionResult or raises DecisionValidationError on stale/invalid results.
    """
    state = {"context": context}
    out = _compiled_graph.invoke(state)
    dr: DecisionResult = out.get("decision_result")
    return dr
