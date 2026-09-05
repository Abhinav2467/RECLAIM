from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Dict, Any

from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from app.db.models import RecoveryCase, ExecutionRecord, Payment
from app.db.repositories.recovery import RecoveryRepository, PostgresIdempotencyStore
from app.domain.states import RecoveryStatus
from app.domain.context_builder import build_decision_context
from app.agents.decision_agent import run_decision_agent
from app.domain.policy import evaluate_policy, PolicyContext, PolicyMode, PolicyDecision
from app.domain.execution import ExecutionManager, RecoveryProvider, ExecutionResult
from app.domain.verification import verify_execution, VerificationResult


def _to_json_safe(obj: Any) -> Any:
    """Helper to convert non-JSON-serializable objects (datetime, Decimal) into strings before JSONB storage."""
    if isinstance(obj, dict):
        return {str(k): _to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_json_safe(v) for v in obj]
    if isinstance(obj, (datetime, Decimal)):
        return str(obj)
    return obj


class MockDefaultProvider:
    """Default provider adapter used if no explicit provider is passed to pipeline."""
    def __init__(self, behavior: str = "success", provider_reference: str = "prov-ref-default"):
        self.behavior = behavior
        self.provider_reference = provider_reference

    def execute(self, action: str, context: Any, idempotency_key: str):
        if self.behavior == "success":
            return type("R", (), {"status": "success", "provider_reference": self.provider_reference, "message": f"executed {action}", "evidence": {"action": action}})()
        if self.behavior == "failed":
            return type("R", (), {"status": "failed", "provider_reference": None, "message": f"failed {action}", "evidence": {}})()
        if self.behavior == "pending":
            return type("R", (), {"status": "pending", "provider_reference": self.provider_reference, "message": f"pending {action}", "evidence": {}})()
        return type("R", (), {"status": "rejected", "provider_reference": None, "message": f"rejected {action}", "evidence": {}})()


def process_recovery_pipeline(
    db: Session,
    merchant_id: int,
    payment_id: Optional[int] = None,
    order_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    trigger_reason: str = "PAYMENT_FAILURE",
    mode: PolicyMode = "AUTONOMOUS",
    merchant_kill_switch: bool = False,
    provider: Optional[RecoveryProvider] = None,
    intervention_costs: Optional[Dict[str, Decimal]] = None,
) -> Optional[RecoveryCase]:
    """End-to-end recovery pipeline orchestrator.

    1. PAYMENT_FAILURE: Finds or creates a RecoveryCase, runs full decision, policy, execution & initial verification.
    2. PAYMENT_CAPTURED: Finds an existing active VERIFYING RecoveryCase and performs authoritative re-verification.
    """
    repo = RecoveryRepository(db=db)

    # Special handling for PAYMENT_CAPTURED re-verification path
    if trigger_reason == "PAYMENT_CAPTURED":
        case: Optional[RecoveryCase] = None
        if payment_id is not None:
            case = db.execute(
                select(RecoveryCase).where(
                    RecoveryCase.merchant_id == merchant_id,
                    RecoveryCase.payment_id == payment_id,
                    RecoveryCase.status == RecoveryStatus.VERIFYING,
                )
            ).scalars().first()

        if case is None and order_id is not None:
            case = db.execute(
                select(RecoveryCase).where(
                    RecoveryCase.merchant_id == merchant_id,
                    RecoveryCase.order_id == order_id,
                    RecoveryCase.status == RecoveryStatus.VERIFYING,
                )
            ).scalars().first()

        if case is None:
            # No existing VERIFYING case; do NOT create a new case for captured payment
            return None

        # Build fresh context with updated DB state (payment is now captured)
        context = build_decision_context(
            db=db,
            order_id=case.order_id,
            payment_id=case.payment_id,
            case_id=case.id,
            context_version=case.context_version or 1,
        )

        # Retrieve existing execution record for this case
        exec_rec = None
        if case.execution_id:
            exec_rec = repo._execution_record_by_execution_id(case.execution_id)
        if exec_rec is None:
            exec_rec = db.execute(
                select(ExecutionRecord).where(ExecutionRecord.recovery_case_id == case.id)
            ).scalars().first()

        if exec_rec is None:
            return case

        # Resolve provider reference from execution record or linked payment
        provider_ref = exec_rec.provider_reference
        if not provider_ref and payment_id is not None:
            p_row = db.get(Payment, payment_id)
            if p_row:
                provider_ref = p_row.provider_payment_id

        exec_result = ExecutionResult(
            action=exec_rec.action,
            status=exec_rec.status or "EXECUTED",
            execution_id=case.execution_id or f"exec-{exec_rec.action}-{exec_rec.idempotency_key}",
            started_at=exec_rec.started_at or datetime.now(timezone.utc),
            completed_at=exec_rec.completed_at,
            provider_reference=provider_ref,
            message=(exec_rec.result.get("message") if exec_rec.result else ""),
            evidence=exec_rec.result or {},
        )

        # Re-verify execution against fresh revenue truth
        verif_result = verify_execution(exec_result, context)
        repo.record_verification(
            execution_id=exec_result.execution_id,
            verification_outcome=verif_result.status,
            evidence=_to_json_safe(verif_result.evidence),
        )

        if verif_result.status == "RECOVERED" and verif_result.verified:
            case = repo.update_case_with_version(
                case.id,
                case.version,
                {
                    "status": RecoveryStatus.RECOVERED,
                    "verification_outcome": RecoveryStatus.RECOVERED,
                },
            )
            if case:
                repo.append_event(
                    recovery_case_id=case.id,
                    event_type="RECOVERY_VERIFIED",
                    actor="system",
                    action=exec_result.action,
                    status=RecoveryStatus.RECOVERED,
                    idempotency_key=f"reverif-case-{case.id}-v{case.version}",
                    evidence=_to_json_safe(verif_result.evidence),
                    message="Revenue recovery verified from authoritative captured payment state",
                )
        elif verif_result.status == "FAILED":
            case = repo.update_case_with_version(
                case.id,
                case.version,
                {
                    "status": RecoveryStatus.FAILED,
                    "verification_outcome": verif_result.status,
                },
            )

        return case

    # Standard PAYMENT_FAILURE pipeline execution path
    case: Optional[RecoveryCase] = None

    if payment_id is not None:
        case = db.execute(
            select(RecoveryCase).where(
                RecoveryCase.merchant_id == merchant_id,
                RecoveryCase.payment_id == payment_id,
                RecoveryCase.status.not_in([
                    RecoveryStatus.RECOVERED,
                    RecoveryStatus.NO_ACTION,
                    RecoveryStatus.NOT_RECOVERABLE,
                    RecoveryStatus.FAILED,
                    RecoveryStatus.ABORTED,
                ])
            )
        ).scalars().first()

    if case is None and order_id is not None:
        case = db.execute(
            select(RecoveryCase).where(
                RecoveryCase.merchant_id == merchant_id,
                RecoveryCase.order_id == order_id,
                RecoveryCase.status.not_in([
                    RecoveryStatus.RECOVERED,
                    RecoveryStatus.NO_ACTION,
                    RecoveryStatus.NOT_RECOVERABLE,
                    RecoveryStatus.FAILED,
                    RecoveryStatus.ABORTED,
                ])
            )
        ).scalars().first()

    details_dict = {"trigger_reason": trigger_reason}
    if intervention_costs:
        details_dict["intervention_costs"] = {k: str(v) for k, v in intervention_costs.items()}

    if case is None:
        case = repo.create_case(
            merchant_id=merchant_id,
            customer_id=customer_id,
            order_id=order_id,
            payment_id=payment_id,
            status=RecoveryStatus.DETECTED,
            reason=trigger_reason,
            details=_to_json_safe(details_dict),
            context_version=1,
            recoverable_amount=None,
            currency=None,
        )
        repo.append_event(
            recovery_case_id=case.id,
            event_type="CASE_CREATED",
            actor="system",
            action="create_case",
            status=case.status,
            idempotency_key=f"create-case-{case.id}",
            evidence=_to_json_safe({"payment_id": payment_id, "order_id": order_id}),
            message=f"Recovery case created for {trigger_reason}",
        )
    elif intervention_costs:
        existing_details = case.details if isinstance(case.details, dict) else {}
        existing_details["intervention_costs"] = {k: str(v) for k, v in intervention_costs.items()}
        repo.update_case_with_version(case.id, case.version, {"details": _to_json_safe(existing_details)})

    # 2. Build DecisionContext
    context = build_decision_context(
        db=db,
        order_id=case.order_id,
        payment_id=case.payment_id,
        case_id=case.id,
        context_version=case.context_version or 1,
        intervention_costs=intervention_costs,
    )

    # Update case with diagnosis and revenue metrics
    diag_str = context.diagnosis.diagnosis if context.diagnosis else None
    conf_str = context.diagnosis.confidence if context.diagnosis else None
    recoverable_amt = context.revenue_truth.recoverable_amount
    curr_str = context.revenue_truth.currency

    case = repo.update_case_with_version(
        case.id,
        case.version,
        {
            "status": RecoveryStatus.DIAGNOSED,
            "diagnosis": diag_str,
            "diagnosis_confidence": conf_str,
            "recoverable_amount": recoverable_amt,
            "currency": curr_str,
        },
    )
    if case is None:
        return None

    repo.append_event(
        recovery_case_id=case.id,
        event_type="DIAGNOSIS_COMPLETED",
        actor="system",
        action="diagnose",
        status=case.status,
        idempotency_key=f"diagnose-case-{case.id}-v{case.version}",
        evidence=_to_json_safe(context.diagnosis.evidence if context.diagnosis else {}),
        message=f"Diagnosis: {diag_str}",
    )

    # 3. LangGraph Decision Agent
    decision_result = run_decision_agent(context)

    # Audit decision
    repo.append_event(
        recovery_case_id=case.id,
        event_type="DECISION_MADE",
        actor="system",
        action=decision_result.recommended_action,
        status=decision_result.decision,
        idempotency_key=f"decision-case-{case.id}-v{case.version}",
        evidence=_to_json_safe(decision_result.evidence),
        message=decision_result.rationale,
    )

    if decision_result.decision == "NO_ACTION":
        case = repo.update_case_with_version(
            case.id,
            case.version,
            {
                "status": RecoveryStatus.NO_ACTION,
                "recommended_action": None,
            },
        )
        repo.append_event(
            recovery_case_id=case.id,
            event_type="PIPELINE_COMPLETED",
            actor="system",
            action=None,
            status=RecoveryStatus.NO_ACTION,
            idempotency_key=f"no-action-case-{case.id}-v{case.version}",
            evidence=_to_json_safe(decision_result.evidence),
            message="No action recommended by Decision Agent",
        )
        return case

    if decision_result.decision == "NEEDS_REVIEW":
        case = repo.update_case_with_version(
            case.id,
            case.version,
            {
                "status": RecoveryStatus.ESCALATED,
                "recommended_action": None,
            },
        )
        repo.append_event(
            recovery_case_id=case.id,
            event_type="ESCALATED_FOR_REVIEW",
            actor="system",
            action=None,
            status=RecoveryStatus.ESCALATED,
            idempotency_key=f"escalated-case-{case.id}-v{case.version}",
            evidence=_to_json_safe(decision_result.evidence),
            message=decision_result.rationale,
        )
        return case

    # Update case with recommendation
    case = repo.update_case_with_version(
        case.id,
        case.version,
        {
            "status": RecoveryStatus.RECOMMENDATION_READY,
            "recommended_action": decision_result.recommended_action,
        },
    )
    if case is None:
        return None

    # 4. Policy Engine
    policy_context = PolicyContext(
        decision_context=context,
        decision_result=decision_result,
        merchant_kill_switch=merchant_kill_switch,
        mode=mode,
        remaining_budget=Decimal("10000.00"),
        contact_count=0,
        max_contacts=3,
    )
    policy_decision = evaluate_policy(policy_context)

    policy_dict = _to_json_safe({
        "decision": policy_decision.decision,
        "approved": policy_decision.approved,
        "reasons": policy_decision.reasons,
        "constraints": policy_decision.constraints,
    })

    if not policy_decision.approved or policy_decision.decision != "APPROVED":
        # Policy blocked
        case = repo.update_case_with_version(
            case.id,
            case.version,
            {
                "status": RecoveryStatus.ABORTED,
                "policy_decision": policy_dict,
            },
        )
        repo.append_event(
            recovery_case_id=case.id,
            event_type="POLICY_BLOCKED",
            actor="system",
            action=decision_result.recommended_action,
            status=RecoveryStatus.ABORTED,
            idempotency_key=f"policy-blocked-case-{case.id}-v{case.version}",
            evidence=_to_json_safe({"reasons": policy_decision.reasons, "constraints": policy_decision.constraints}),
            message=f"Policy decision {policy_decision.decision}: {', '.join(policy_decision.reasons)}",
        )
        return case

    case = repo.update_case_with_version(
        case.id,
        case.version,
        {
            "status": RecoveryStatus.APPROVED,
            "policy_decision": policy_dict,
        },
    )
    if case is None:
        return None

    # 5. Execution Engine
    idempotency_store = PostgresIdempotencyStore(db=db)
    exec_mgr = ExecutionManager(idempotency_store=idempotency_store)
    active_provider = provider or MockDefaultProvider()

    idempotency_key = f"rec-case-{case.id}-v{case.version}-{policy_decision.action}"

    exec_result = exec_mgr.execute(
        policy_decision=policy_decision,
        context=context,
        idempotency_key=idempotency_key,
        provider=active_provider,
    )

    # Link recovery_case_id on ExecutionRecord
    exec_rec = repo.get_execution_record(policy_decision.action, idempotency_key)
    if exec_rec and exec_rec.recovery_case_id is None:
        exec_rec.recovery_case_id = case.id
        db.add(exec_rec)
        db.commit()

    case = repo.update_case_with_version(
        case.id,
        case.version,
        {
            "status": RecoveryStatus.EXECUTING,
            "execution_id": exec_result.execution_id,
        },
    )
    if case is None:
        return None

    repo.append_event(
        recovery_case_id=case.id,
        event_type="EXECUTION_ATTEMPTED",
        actor="system",
        action=exec_result.action,
        status=exec_result.status,
        idempotency_key=idempotency_key,
        evidence=_to_json_safe(exec_result.evidence),
        message=f"Execution status: {exec_result.status}",
    )

    # 6. Verification
    verif_result = verify_execution(exec_result, context)
    repo.record_verification(
        execution_id=exec_result.execution_id,
        verification_outcome=verif_result.status,
        evidence=_to_json_safe(verif_result.evidence),
    )

    # Determine final RecoveryCase status
    if verif_result.status == "RECOVERED" and verif_result.verified:
        final_status = RecoveryStatus.RECOVERED
    elif verif_result.status == "FAILED":
        final_status = RecoveryStatus.FAILED
    else:
        # PENDING, NOT_RECOVERED, UNKNOWN
        final_status = RecoveryStatus.VERIFYING

    case = repo.update_case_with_version(
        case.id,
        case.version,
        {
            "status": final_status,
            "verification_outcome": verif_result.status,
        },
    )
    return case
