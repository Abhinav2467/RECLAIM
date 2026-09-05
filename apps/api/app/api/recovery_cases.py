from datetime import datetime, timezone
from decimal import Decimal
import json
import asyncio
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request, status
from starlette.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.deps import get_db
from app.db.models import RecoveryCase, ExecutionRecord, RecoveryAuditEvent, User
from app.api.auth import get_current_active_user
from app.domain.revenue_truth import assess_order_revenue, RevenueTruthResult, ContributingPayment

from app.domain.diagnosis import DiagnosisResult
from app.domain.actions import generate_candidates
from app.domain.probability import estimate
from app.domain.economics import evaluate_batch
from app.domain.context_builder import DEFAULT_INTERVENTION_COSTS
from app.domain.summary import generate_executive_summary

router = APIRouter(tags=["recovery-cases"])

TERMINAL_CASE_STATUSES = {"RECOVERED", "NO_ACTION", "FAILED", "ABORTED"}


# --- PYDANTIC READ MODELS FOR OVERVIEW ---

class MerchantOverviewCounts(BaseModel):
    total_cases: int
    active_cases: int
    verifying_cases: int
    recovered_cases: int
    no_action_cases: int
    failed_cases: int


class MerchantOverviewAggregates(BaseModel):
    revenue_at_risk: str
    recovered_amount: str
    expected_recovery: str
    capital_preserved: str
    currency: str = "USD"


class MerchantOverviewCaseItem(BaseModel):
    case_id: int
    customer_display: str
    order_external_id: str
    provider_payment_id: str
    recoverable_amount: str
    current_at_risk_amount: str
    currency: str
    diagnosis: Optional[str] = None
    recommended_action: Optional[str] = None
    status: str
    verification_outcome: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    decision_expected_net_recovery: Optional[str] = None


class MerchantRecoveryOverviewResponse(BaseModel):
    merchant_id: int
    counts: MerchantOverviewCounts
    aggregates: MerchantOverviewAggregates
    cases: List[MerchantOverviewCaseItem]


def _reconstruct_decision_time_evaluations(case: RecoveryCase) -> List[Dict[str, Any]]:
    """Reconstruct decision-time candidate action evaluations using authoritative decision-time case fields.

    Uses decision-time diagnosis, recoverable_amount, and payment provenance rather than post-recovery current DB state.
    """
    if not case.diagnosis or case.recoverable_amount is None:
        return []

    try:
        rec_amt = Decimal(str(case.recoverable_amount))
        diag_str = case.diagnosis
        curr_str = case.currency or "USD"
        now_ts = case.created_at if case.created_at else datetime.now(tz=timezone.utc)

        # Build evidence including payment provenance from case.payment if present
        evidence: Dict[str, Any] = {
            "case_id": case.id,
            "payment_id": case.payment_id,
            "authorization_row_id": True,
        }
        if case.payment:
            if case.payment.provider_event_id:
                evidence["provider_event_id"] = case.payment.provider_event_id
                evidence["payment.provider_event_id"] = case.payment.provider_event_id
            if case.payment.provider_state_at:
                evidence["provider_state_at"] = case.payment.provider_state_at
                evidence["payment.provider_state_at"] = case.payment.provider_state_at

        diag_result = DiagnosisResult(
            diagnosis=diag_str,
            confidence=case.diagnosis_confidence or "HIGH",
            order_id=case.order_id,
            payment_ids=[case.payment_id] if case.payment_id else [],
            evidence=evidence,
            suggested_actions=[case.recommended_action] if case.recommended_action else [],
            diagnosis_timestamp=now_ts,
            notes=f"Diagnosis: {diag_str}",
        )

        prov_state = "authorized" if diag_str == "AUTHORIZATION_STALE" else "failed"
        payment_ref = case.payment.provider_payment_id if case.payment else "pay_ref"

        cp = ContributingPayment(
            payment_id=case.payment_id or 1,
            provider_payment_id=payment_ref,
            amount=rec_amt,
            currency=curr_str,
            provider_state=prov_state,
            provider_event_id=case.payment.provider_event_id if case.payment else "evt_ref",
            provider_state_at=case.payment.provider_state_at if case.payment else None,
        )

        rev_truth = RevenueTruthResult(
            order_id=case.order_id or 1,
            expected_amount=rec_amt,
            captured_amount=Decimal("0.00"),
            currency=curr_str,
            recoverable_amount=rec_amt,
            resolution="complete",
            contributing_payments=[cp],
        )

        candidates = generate_candidates(diag_result, rev_truth)
        probabilities = {cand.action: estimate(diag_result, rev_truth, cand.action, now=now_ts) for cand in candidates}
        economic_evals = evaluate_batch(candidates, probabilities, rev_truth, DEFAULT_INTERVENTION_COSTS)

        eval_map = {e.action: e for e in economic_evals}

        action_evaluations: List[Dict[str, Any]] = []
        for candidate in candidates:
            econ = eval_map.get(candidate.action)
            is_selected = (case.recommended_action == candidate.action)
            eligible = candidate.eligible
            viable = econ.economically_viable if econ else False

            why_not_val = None
            if not eligible:
                why_not_val = candidate.reason
            elif econ and not viable:
                why_not_val = econ.reason

            action_evaluations.append({
                "action": candidate.action,
                "eligible": eligible,
                "economically_viable": viable,
                "is_selected": is_selected,
                "expected_net_recovery": str(econ.expected_net_recovery) if (econ and econ.expected_net_recovery is not None) else None,
                "success_probability": float(econ.success_probability) if (econ and econ.success_probability is not None) else None,
                "intervention_cost": str(econ.intervention_cost) if (econ and econ.intervention_cost is not None) else None,
                "why_not": why_not_val,
            })
        return action_evaluations
    except Exception:
        return []


@router.get("/recovery/overview", response_model=MerchantRecoveryOverviewResponse)
@router.get("/recovery-cases/overview", response_model=MerchantRecoveryOverviewResponse)
def get_merchant_recovery_overview(
    merchant_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> MerchantRecoveryOverviewResponse:
    """Read-only merchant recovery overview endpoint providing authoritative aggregate performance & full case ledger.

    Enforces authenticated session and merchant isolation.
    """
    if merchant_id is not None and merchant_id != current_user.merchant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot access another merchant's operational data",
        )

    target_merchant_id = current_user.merchant_id


    cases_query = db.execute(
        select(RecoveryCase)
        .where(RecoveryCase.merchant_id == target_merchant_id)
        .order_by(RecoveryCase.updated_at.desc())
    ).scalars().all()

    total_cases = len(cases_query)
    active_cases = 0
    verifying_cases = 0
    recovered_cases = 0
    no_action_cases = 0
    failed_cases = 0

    tot_at_risk = Decimal("0.00")
    tot_recovered = Decimal("0.00")
    tot_expected_recovery = Decimal("0.00")
    tot_capital_preserved = Decimal("0.00")

    case_items: List[MerchantOverviewCaseItem] = []

    for c in cases_query:
        st_str = str(c.status).upper()

        if st_str == "VERIFYING":
            verifying_cases += 1
            active_cases += 1
        elif st_str == "RECOVERED":
            recovered_cases += 1
        elif st_str == "NO_ACTION":
            no_action_cases += 1
        elif st_str in {"FAILED", "ABORTED", "NOT_RECOVERABLE"}:
            failed_cases += 1
        else:
            if st_str not in TERMINAL_CASE_STATUSES:
                active_cases += 1

        # Reconstruct decision-time candidate action evaluations for expected_net_recovery
        evals = _reconstruct_decision_time_evaluations(c)
        selected_eval = next((e for e in evals if e.get("is_selected")), None)
        selected_expected_net = selected_eval.get("expected_net_recovery") if selected_eval else None

        dec_recoverable = Decimal(str(c.recoverable_amount or "0.00"))

        is_term = st_str in TERMINAL_CASE_STATUSES
        is_cap = (c.payment and c.payment.provider_state == "captured") or st_str == "RECOVERED" or c.verification_outcome == "RECOVERED"

        if is_cap or st_str == "NO_ACTION":
            curr_at_risk = Decimal("0.00")
        else:
            curr_at_risk = dec_recoverable

        if not is_term and curr_at_risk > Decimal("0.00"):
            tot_at_risk += curr_at_risk

        if st_str == "RECOVERED" or c.verification_outcome == "RECOVERED":
            tot_recovered += dec_recoverable

        if selected_expected_net is not None and c.recommended_action:
            tot_expected_recovery += Decimal(str(selected_expected_net))

        if st_str == "NO_ACTION":
            tot_capital_preserved += dec_recoverable

        cust_disp = (
            (c.customer.name or c.customer.external_id) if c.customer
            else (c.order.customer.name if c.order and c.order.customer else None)
        ) or f"Customer #{c.customer_id or 1001}"

        ord_ext = (c.order.external_id if c.order else None) or f"ord_demo_{c.id}"
        pay_ext = (c.payment.provider_payment_id if c.payment else None) or f"pay_demo_{c.id}"

        case_items.append(
            MerchantOverviewCaseItem(
                case_id=c.id,
                customer_display=cust_disp,
                order_external_id=ord_ext,
                provider_payment_id=pay_ext,
                recoverable_amount=f"{dec_recoverable:.2f}",
                current_at_risk_amount=f"{curr_at_risk:.2f}",
                currency=c.currency or "USD",
                diagnosis=c.diagnosis,
                recommended_action=c.recommended_action,
                status=str(c.status),
                verification_outcome=c.verification_outcome,
                created_at=c.created_at.isoformat() if c.created_at else None,
                updated_at=c.updated_at.isoformat() if c.updated_at else None,
                decision_expected_net_recovery=str(selected_expected_net) if selected_expected_net is not None else None,
            )
        )

    return MerchantRecoveryOverviewResponse(
        merchant_id=target_merchant_id,
        counts=MerchantOverviewCounts(
            total_cases=total_cases,
            active_cases=active_cases,
            verifying_cases=verifying_cases,
            recovered_cases=recovered_cases,
            no_action_cases=no_action_cases,
            failed_cases=failed_cases,
        ),
        aggregates=MerchantOverviewAggregates(
            revenue_at_risk=f"{tot_at_risk:.2f}",
            recovered_amount=f"{tot_recovered:.2f}",
            expected_recovery=f"{tot_expected_recovery:.2f}",
            capital_preserved=f"{tot_capital_preserved:.2f}",
            currency="USD",
        ),
        cases=case_items,
    )


@router.get("/recovery-cases/{case_id}")
def get_recovery_case(
    case_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve full details for a recovery case including decision snapshot & current state.

    Enforces authenticated session and merchant isolation.
    """
    case = db.execute(
        select(RecoveryCase).where(RecoveryCase.id == case_id)
    ).scalars().first()

    if case is None or case.merchant_id != current_user.merchant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recovery case #{case_id} not found",
        )

    order_ext_id = case.order.external_id if case.order else None
    prov_payment_id = case.payment.provider_payment_id if case.payment else None

    # Execution record lookup
    exec_rec = db.execute(
        select(ExecutionRecord).where(ExecutionRecord.recovery_case_id == case.id)
    ).scalars().first()

    execution_dict: Optional[Dict[str, Any]] = None
    if exec_rec:
        execution_dict = {
            "execution_id": case.execution_id or f"exec-{exec_rec.action}-{exec_rec.idempotency_key}",
            "action": exec_rec.action,
            "status": exec_rec.status,
            "provider_reference": exec_rec.provider_reference,
            "started_at": exec_rec.started_at.isoformat() if exec_rec.started_at else None,
            "completed_at": exec_rec.completed_at.isoformat() if exec_rec.completed_at else None,
        }

    # Audit events
    events = db.execute(
        select(RecoveryAuditEvent)
        .where(RecoveryAuditEvent.recovery_case_id == case.id)
        .order_by(RecoveryAuditEvent.occurred_at.asc())
    ).scalars().all()

    audit_list: List[Dict[str, Any]] = [
        {
            "id": ev.id,
            "event_type": ev.event_type,
            "occurred_at": ev.occurred_at.isoformat() if ev.occurred_at else None,
            "actor": ev.actor,
            "action": ev.action,
            "status": ev.status,
            "message": ev.message,
        }
        for ev in events
    ]

    # Extract decision status & rationale from audit trail
    decision_str: Optional[str] = None
    decision_rationale_str: Optional[str] = None
    for ev in events:
        if ev.event_type == "DECISION_MADE":
            decision_str = ev.status
            decision_rationale_str = ev.message
            break

    # 1. Reconstruct decision-time candidate action evaluations using decision-time state & provenance
    decision_action_evaluations = _reconstruct_decision_time_evaluations(case)

    # 2. Assess current revenue truth from DB state
    current_payment_state = case.payment.provider_state if case.payment else None
    current_recoverable_amount: Optional[str] = None
    try:
        current_revenue_truth = assess_order_revenue(db, case.order_id)
        current_recoverable_amount = str(current_revenue_truth.recoverable_amount)
    except Exception:
        current_recoverable_amount = "0.0000" if case.status == "RECOVERED" else str(case.recoverable_amount or "0")

    decision_snapshot = {
        "recoverable_amount": str(case.recoverable_amount) if case.recoverable_amount is not None else None,
        "currency": case.currency,
        "diagnosis": case.diagnosis,
        "diagnosis_confidence": case.diagnosis_confidence,
        "recommended_action": case.recommended_action,
        "decision": decision_str,
        "decision_rationale": decision_rationale_str,
        "policy": case.policy_decision,
        "context_version": case.context_version,
        "action_evaluations": decision_action_evaluations,
    }

    current_state = {
        "recoverable_amount": current_recoverable_amount,
        "currency": case.currency,
        "payment_state": current_payment_state,
        "case_status": str(case.status),
        "verification_outcome": case.verification_outcome,
    }

    # 3. Generate non-authoritative presentation summary downstream of authoritative decision snapshot
    executive_summary = generate_executive_summary(decision_snapshot)

    return {
        "case_id": case.id,
        "status": str(case.status),
        "version": case.version,
        "merchant_id": case.merchant_id,
        "customer_id": case.customer_id,
        "order_id": case.order_id,
        "order_external_id": order_ext_id,
        "payment_id": case.payment_id,
        "provider_payment_id": prov_payment_id,
        # Authoritative decision snapshot vs current state
        "decision_snapshot": decision_snapshot,
        "current_state": current_state,
        # Non-authoritative presentation summary
        "executive_summary": executive_summary,
        # Backwards compatibility top-level fields
        "diagnosis": case.diagnosis,
        "diagnosis_confidence": case.diagnosis_confidence,
        "recoverable_amount": str(case.recoverable_amount) if case.recoverable_amount is not None else None,
        "currency": case.currency,
        "recommended_action": case.recommended_action,
        "decision": decision_str,
        "decision_rationale": decision_rationale_str,
        "context_version": case.context_version,
        "policy_decision": case.policy_decision,
        "execution": execution_dict,
        "verification_outcome": case.verification_outcome,
        "created_at": case.created_at.isoformat() if case.created_at else None,
        "updated_at": case.updated_at.isoformat() if case.updated_at else None,
        "action_evaluations": decision_action_evaluations,
        "audit_events": audit_list,
    }


@router.get("/recovery-cases/{case_id}/stream")
async def stream_recovery_case_events(
    case_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Stream SSE notifications whenever new audit events are appended to a recovery case.

    Includes client disconnect detection and initial event state payload. Enforces merchant scoping.
    """
    case = db.execute(
        select(RecoveryCase).where(RecoveryCase.id == case_id)
    ).scalars().first()

    if case is None or case.merchant_id != current_user.merchant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recovery case #{case_id} not found",
        )


    async def event_generator():
        last_event_header = request.headers.get("Last-Event-ID") or request.query_params.get("last_event_id")
        cursor_id = int(last_event_header) if last_event_header and last_event_header.isdigit() else 0
        last_event_id = cursor_id

        initial_events = db.execute(
            select(RecoveryAuditEvent)
            .where(
                RecoveryAuditEvent.recovery_case_id == case_id,
                RecoveryAuditEvent.id > cursor_id,
            )
            .order_by(RecoveryAuditEvent.id.asc())
        ).scalars().all()

        if initial_events:
            last_event_id = initial_events[-1].id
            initial_data = [
                {
                    "id": ev.id,
                    "event_type": ev.event_type,
                    "occurred_at": ev.occurred_at.isoformat() if ev.occurred_at else None,
                    "status": ev.status,
                    "message": ev.message,
                }
                for ev in initial_events
            ]
            yield f"event: initial_state\ndata: {json.dumps({'case_id': case_id, 'events': initial_data})}\n\n"

        while True:
            if await request.is_disconnected():
                break

            new_events = db.execute(
                select(RecoveryAuditEvent)
                .where(
                    RecoveryAuditEvent.recovery_case_id == case_id,
                    RecoveryAuditEvent.id > last_event_id,
                )
                .order_by(RecoveryAuditEvent.id.asc())
            ).scalars().all()

            for ev in new_events:
                last_event_id = ev.id
                payload = {
                    "case_id": case_id,
                    "event_id": ev.id,
                    "event_type": ev.event_type,
                    "occurred_at": ev.occurred_at.isoformat() if ev.occurred_at else None,
                    "status": ev.status,
                    "message": ev.message,
                }
                yield f"event: audit_event\ndata: {json.dumps(payload)}\n\n"

            case_current = db.execute(
                select(RecoveryCase).where(RecoveryCase.id == case_id)
            ).scalars().first()
            if case_current and case_current.status in ("RECOVERED", "NO_ACTION", "FAILED"):
                yield f"event: terminal\ndata: {json.dumps({'case_id': case_id, 'terminal': True, 'status': case_current.status})}\n\n"
                break

            await asyncio.sleep(1.0)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
