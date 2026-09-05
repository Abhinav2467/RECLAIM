import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.deps import get_db
from app.db.models import Merchant, Customer, Order, Payment, RecoveryCase, User
from app.api.auth import get_optional_current_user
from app.services.recovery_pipeline import process_recovery_pipeline, MockDefaultProvider

router = APIRouter(tags=["demo"])

DEMO_AMOUNTS: List[Decimal] = [
    Decimal("47.00"),
    Decimal("89.00"),
    Decimal("149.00"),
    Decimal("249.00"),
    Decimal("320.00"),
    Decimal("499.00"),
    Decimal("780.00"),
    Decimal("1250.00"),
    Decimal("1499.00"),
    Decimal("2400.00"),
]

SYNTHETIC_MERCHANTS: List[str] = [
    "Northstar Foods",
    "Orbit Retail",
    "Meridian Labs",
    "Acme Health",
    "Kora Systems",
    "Vertex Commerce",
    "Aura Logistics",
    "Pinnacle Brands",
    "Cascade Digital",
    "Solstice Media",
]

DEMO_CURRENCY = "USD"


class DemoScenarioRequest(BaseModel):
    demo_run_id: Optional[str] = None


class DemoCaptureRequest(BaseModel):
    demo_run_id: Optional[str] = None
    case_id: Optional[int] = None


class DemoBatchRequest(BaseModel):
    batch_run_id: Optional[str] = None


def _check_demo_env_guard() -> None:
    if getattr(settings, "app_env", "development").lower() == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo scenario endpoints are disabled in production environments",
        )


def _get_clean_run_id(demo_run_id: Optional[str]) -> tuple[str, str]:
    if not demo_run_id or not str(demo_run_id).strip():
        demo_run_id = str(uuid.uuid4())
    clean_suffix = str(demo_run_id).replace("-", "").replace("_", "").lower()[:12]
    return demo_run_id, clean_suffix


def _get_deterministic_amount(clean_suffix: str, default_idx: int = 3) -> Decimal:
    """Deterministically select plausible transaction amount from clean_suffix hash."""
    try:
        val = int(clean_suffix[:6], 16)
        return DEMO_AMOUNTS[val % len(DEMO_AMOUNTS)]
    except ValueError:
        return DEMO_AMOUNTS[default_idx % len(DEMO_AMOUNTS)]


def _get_synthetic_name(clean_suffix: str) -> str:
    """Deterministically select plausible customer name from clean_suffix hash."""
    try:
        val = int(clean_suffix[-6:], 16)
        return SYNTHETIC_MERCHANTS[val % len(SYNTHETIC_MERCHANTS)]
    except ValueError:
        return SYNTHETIC_MERCHANTS[0]


@router.post("/demo/recovery-scenario")
def seed_demo_recovery_scenario(
    req: Optional[DemoScenarioRequest] = None,
    demo_run_id: Optional[str] = Query(None),
    user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Create or resolve an idempotent demo recovery scenario run (AUTHORIZATION_STALE).

    1. Checks environment guard (disabled in production).
    2. Resolves unique demo_run_id (generates UUID if omitted).
    3. Deterministically selects transaction amount and customer name.
    4. Derives external identifiers: cust_demo_<suffix>, ord_demo_<suffix>, pay_demo_<suffix>.
    5. If scenario run already exists, returns existing case idempotently.
    6. If new run, creates records and triggers recovery pipeline.
    7. Returns scenario state (RecoveryCase in VERIFYING status).
    """
    _check_demo_env_guard()

    input_run_id = (req.demo_run_id if req and req.demo_run_id else None) or demo_run_id
    run_id, clean_suffix = _get_clean_run_id(input_run_id)

    amount = _get_deterministic_amount(clean_suffix, default_idx=3)  # default $249.00
    customer_name = _get_synthetic_name(clean_suffix)

    merchant_id = user.merchant_id if user and hasattr(user, "merchant_id") else settings.razorpay_merchant_id
    merchant = db.get(Merchant, merchant_id)
    if merchant is None:
        merchant = Merchant(id=merchant_id, name="Demo Merchant Inc.", metadata_json={"demo": True})
        db.add(merchant)
        db.commit()

    ext_customer_id = f"cust_demo_{clean_suffix}"
    ext_order_id = f"ord_demo_{clean_suffix}"
    provider_payment_id = f"pay_demo_{clean_suffix}"

    # Check if order and payment already exist for this run ID
    order = db.execute(
        select(Order).where(
            Order.merchant_id == merchant.id,
            Order.external_id == ext_order_id,
        )
    ).scalars().first()

    payment = db.execute(
        select(Payment).where(
            Payment.merchant_id == merchant.id,
            Payment.provider_payment_id == provider_payment_id,
        )
    ).scalars().first()

    if order and payment:
        case = db.execute(
            select(RecoveryCase).where(
                RecoveryCase.merchant_id == merchant.id,
                RecoveryCase.order_id == order.id,
            )
        ).scalars().first()

        if case:
            return {
                "status": "success",
                "scenario": "demo_stale_authorization_recovery",
                "demo_run_id": run_id,
                "case_id": case.id,
                "case_status": str(case.status),
                "merchant_id": merchant.id,
                "customer_name": customer_name,
                "order_external_id": ext_order_id,
                "provider_payment_id": provider_payment_id,
                "amount": str(order.amount_total),
                "currency": DEMO_CURRENCY,
                "recommended_action": case.recommended_action,
            }

    # 1. Customer
    customer = db.execute(
        select(Customer).where(
            Customer.merchant_id == merchant.id,
            Customer.external_id == ext_customer_id,
        )
    ).scalars().first()

    if customer is None:
        customer = Customer(
            merchant_id=merchant.id,
            external_id=ext_customer_id,
            name=customer_name,
            email=f"demo_{clean_suffix}@example.com",
        )
        db.add(customer)
        db.commit()

    # 2. Order
    if order is None:
        order = Order(
            merchant_id=merchant.id,
            customer_id=customer.id,
            external_id=ext_order_id,
            amount_total=amount,
            currency=DEMO_CURRENCY,
        )
        db.add(order)
        db.commit()

    # 3. Payment in stale authorized state (35 mins old)
    stale_time = datetime.now(tz=timezone.utc) - timedelta(minutes=35)
    if payment is None:
        payment = Payment(
            merchant_id=merchant.id,
            customer_id=customer.id,
            order_id=order.id,
            provider_payment_id=provider_payment_id,
            amount=amount,
            currency=DEMO_CURRENCY,
            status="authorized",
            provider_state="authorized",
            provider_event_id=f"evt_demo_auth_{clean_suffix}",
            provider_state_at=stale_time,
        )
        db.add(payment)
        db.commit()

    # 4. Trigger recovery pipeline
    provider = MockDefaultProvider(behavior="success", provider_reference=provider_payment_id)
    case = process_recovery_pipeline(
        db=db,
        merchant_id=merchant.id,
        payment_id=payment.id,
        order_id=order.id,
        customer_id=customer.id,
        trigger_reason="AUTHORIZATION_STALE",
        provider=provider,
    )

    return {
        "status": "success",
        "scenario": "demo_stale_authorization_recovery",
        "demo_run_id": run_id,
        "case_id": case.id if case else None,
        "case_status": str(case.status) if case else None,
        "merchant_id": merchant.id,
        "customer_name": customer_name,
        "order_external_id": ext_order_id,
        "provider_payment_id": provider_payment_id,
        "amount": str(amount),
        "currency": DEMO_CURRENCY,
        "recommended_action": case.recommended_action if case else None,
    }


@router.post("/demo/recovery-scenario/capture")
def simulate_demo_payment_capture(
    req: Optional[DemoCaptureRequest] = None,
    demo_run_id: Optional[str] = Query(None),
    case_id: Optional[int] = Query(None),
    user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Simulate payment capture for a specific demo run or case.

    1. Checks environment guard.
    2. Identifies target payment via case_id or demo_run_id.
    3. Reconciles payment provider_state to 'captured' in DB.
    4. Triggers process_recovery_pipeline with trigger_reason='PAYMENT_CAPTURED'.
    5. Verifies capture against Revenue Truth and transitions case to RECOVERED.
    """
    _check_demo_env_guard()

    target_case_id = (req.case_id if req and req.case_id else None) or case_id
    target_run_id = (req.demo_run_id if req and req.demo_run_id else None) or demo_run_id

    merchant_id = user.merchant_id if user and hasattr(user, "merchant_id") else settings.razorpay_merchant_id
    payment = None

    if target_case_id:
        case_obj = db.get(RecoveryCase, target_case_id)
        if case_obj:
            payment = db.get(Payment, case_obj.payment_id)
    elif target_run_id:
        _, clean_suffix = _get_clean_run_id(target_run_id)
        provider_payment_id = f"pay_demo_{clean_suffix}"
        payment = db.execute(
            select(Payment).where(
                Payment.merchant_id == merchant_id,
                Payment.provider_payment_id == provider_payment_id,
            )
        ).scalars().first()
    else:
        # Fallback: get the latest authorized demo payment
        payment = db.execute(
            select(Payment)
            .where(
                Payment.merchant_id == merchant_id,
                Payment.provider_payment_id.like("pay_demo_%"),
                Payment.status == "authorized",
            )
            .order_by(Payment.id.desc())
        ).scalars().first()

    if payment is None:
        payment = db.execute(
            select(Payment)
            .where(
                Payment.merchant_id == merchant_id,
                Payment.provider_payment_id.like("pay_demo_%"),
            )
            .order_by(Payment.id.desc())
        ).scalars().first()

    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo scenario payment not found. Call POST /api/demo/recovery-scenario first.",
        )

    # Update payment state to captured
    payment.status = "captured"
    payment.provider_state = "captured"
    payment.provider_event_id = f"evt_demo_cap_{payment.id}"
    payment.provider_state_at = datetime.now(tz=timezone.utc)
    db.add(payment)
    db.commit()

    # Trigger recovery pipeline for captured verification loop
    provider = MockDefaultProvider(behavior="success", provider_reference=payment.provider_payment_id)
    case = process_recovery_pipeline(
        db=db,
        merchant_id=merchant_id,
        payment_id=payment.id,
        order_id=payment.order_id,
        customer_id=payment.customer_id,
        trigger_reason="PAYMENT_CAPTURED",
        provider=provider,
    )

    if case is None:
        case = db.execute(
            select(RecoveryCase).where(
                RecoveryCase.merchant_id == merchant_id,
                RecoveryCase.payment_id == payment.id,
            )
        ).scalars().first()

    res_run_id = target_run_id or (
        payment.provider_payment_id.replace("pay_demo_", "")
        if payment.provider_payment_id.startswith("pay_demo_")
        else "demo_legacy"
    )

    return {
        "status": "success",
        "scenario": "demo_payment_captured_verification",
        "demo_run_id": res_run_id,
        "case_id": case.id if case else None,
        "case_status": str(case.status) if case else None,
        "verification_outcome": case.verification_outcome if case else None,
        "provider_payment_id": payment.provider_payment_id,
        "payment_state": payment.provider_state,
    }


@router.post("/demo/no-action-scenario")
def seed_demo_no_action_scenario(
    req: Optional[DemoScenarioRequest] = None,
    demo_run_id: Optional[str] = Query(None),
    user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Create or resolve an idempotent demo NO_ACTION scenario run.

    Demonstrates capital preservation where revenue IS at risk (e.g. $47.00),
    candidate actions are evaluated, but intervention costs exceed expected gross recovery,
    so Decision Agent naturally returns NO_ACTION.
    """
    _check_demo_env_guard()

    input_run_id = (req.demo_run_id if req and req.demo_run_id else None) or demo_run_id
    run_id, clean_suffix = _get_clean_run_id(input_run_id)

    # Use a deterministic small amount ($47.00 or $35.00) where recovery costs exceed expected gross
    # For NO_ACTION capital preservation demo, use a small amount ($47.00)
    # where intervention cost ($50.00) exceeds expected gross recovery ($47 * 0.65 = $30.55),
    # producing expected_net <= 0 so Decision Agent naturally returns NO_ACTION.
    amount = Decimal("47.00")
    customer_name = _get_synthetic_name(clean_suffix)

    merchant_id = user.merchant_id if user and hasattr(user, "merchant_id") else settings.razorpay_merchant_id
    merchant = db.get(Merchant, merchant_id)
    if merchant is None:
        merchant = Merchant(id=merchant_id, name="Demo Merchant Inc.", metadata_json={"demo": True})
        db.add(merchant)
        db.commit()

    ext_customer_id = f"cust_demo_no_action_{clean_suffix}"
    ext_order_id = f"ord_demo_no_action_{clean_suffix}"
    provider_payment_id = f"pay_demo_no_action_{clean_suffix}"

    # Check if order and payment already exist for this run ID
    order = db.execute(
        select(Order).where(
            Order.merchant_id == merchant.id,
            Order.external_id == ext_order_id,
        )
    ).scalars().first()

    payment = db.execute(
        select(Payment).where(
            Payment.merchant_id == merchant.id,
            Payment.provider_payment_id == provider_payment_id,
        )
    ).scalars().first()

    if order and payment:
        case = db.execute(
            select(RecoveryCase).where(
                RecoveryCase.merchant_id == merchant.id,
                RecoveryCase.order_id == order.id,
            )
        ).scalars().first()

        if case:
            return {
                "status": "success",
                "scenario": "demo_no_action_unviable_recovery",
                "demo_run_id": run_id,
                "case_id": case.id,
                "case_status": str(case.status),
                "merchant_id": merchant.id,
                "customer_name": customer_name,
                "order_external_id": ext_order_id,
                "provider_payment_id": provider_payment_id,
                "amount": str(order.amount_total),
                "currency": DEMO_CURRENCY,
                "recommended_action": case.recommended_action,
            }

    # 1. Customer
    customer = db.execute(
        select(Customer).where(
            Customer.merchant_id == merchant.id,
            Customer.external_id == ext_customer_id,
        )
    ).scalars().first()

    if customer is None:
        customer = Customer(
            merchant_id=merchant.id,
            external_id=ext_customer_id,
            name=customer_name,
            email=f"no_action_{clean_suffix}@example.com",
        )
        db.add(customer)
        db.commit()

    # 2. Order
    if order is None:
        order = Order(
            merchant_id=merchant.id,
            customer_id=customer.id,
            external_id=ext_order_id,
            amount_total=amount,
            currency=DEMO_CURRENCY,
        )
        db.add(order)
        db.commit()

    # 3. Payment in failed state with $47.00 recoverable amount
    now_ts = datetime.now(tz=timezone.utc)
    if payment is None:
        payment = Payment(
            merchant_id=merchant.id,
            customer_id=customer.id,
            order_id=order.id,
            provider_payment_id=provider_payment_id,
            amount=amount,
            currency=DEMO_CURRENCY,
            status="failed",
            provider_state="failed",
            provider_event_id=f"evt_demo_no_action_{clean_suffix}",
            provider_state_at=now_ts,
        )
        db.add(payment)
        db.commit()

    # 4. Trigger recovery pipeline with intervention costs higher than gross recovery
    provider = MockDefaultProvider(behavior="success", provider_reference=provider_payment_id)
    # Pass higher cost thresholds for manual/case creation so small $47.00 payment yields expected_net <= 0
    custom_costs = {
        "attempt_capture_retry": Decimal("50.00"),
        "notify_customer_failure": Decimal("50.00"),
        "send_cart_recovery_email": Decimal("50.00"),
        "offer_discount": Decimal("50.00"),
        "manual_review": Decimal("50.00"),
        "collect_more_evidence": Decimal("50.00"),
        "create_recovery_case": Decimal("50.00"),
    }
    case = process_recovery_pipeline(
        db=db,
        merchant_id=merchant.id,
        payment_id=payment.id,
        order_id=order.id,
        customer_id=customer.id,
        trigger_reason="PAYMENT_FAILURE",
        provider=provider,
        intervention_costs=custom_costs,
    )

    return {
        "status": "success",
        "scenario": "demo_no_action_unviable_recovery",
        "demo_run_id": run_id,
        "case_id": case.id if case else None,
        "case_status": str(case.status) if case else None,
        "merchant_id": merchant.id,
        "customer_name": customer_name,
        "order_external_id": ext_order_id,
        "provider_payment_id": provider_payment_id,
        "amount": str(amount),
        "currency": DEMO_CURRENCY,
        "recommended_action": case.recommended_action if case else None,
    }


@router.post("/demo/checkout-abandonment-scenario")
def seed_demo_checkout_abandonment_scenario(
    req: Optional[DemoScenarioRequest] = None,
    demo_run_id: Optional[str] = Query(None),
    user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Create or resolve an idempotent demo CHECKOUT_ABANDONMENT scenario run.

    Order exists with recoverable amount ($780.00), no payments attempted yet.
    Evaluates cart recovery email and discount candidates.
    """
    _check_demo_env_guard()

    input_run_id = (req.demo_run_id if req and req.demo_run_id else None) or demo_run_id
    run_id, clean_suffix = _get_clean_run_id(input_run_id)

    amount = _get_deterministic_amount(clean_suffix, default_idx=6)  # default $780.00
    customer_name = _get_synthetic_name(clean_suffix)

    merchant_id = user.merchant_id if user and hasattr(user, "merchant_id") else settings.razorpay_merchant_id
    merchant = db.get(Merchant, merchant_id)
    if merchant is None:
        merchant = Merchant(id=merchant_id, name="Demo Merchant Inc.", metadata_json={"demo": True})
        db.add(merchant)
        db.commit()

    ext_customer_id = f"cust_demo_cart_{clean_suffix}"
    ext_order_id = f"ord_demo_cart_{clean_suffix}"

    order = db.execute(
        select(Order).where(
            Order.merchant_id == merchant.id,
            Order.external_id == ext_order_id,
        )
    ).scalars().first()

    if order:
        case = db.execute(
            select(RecoveryCase).where(
                RecoveryCase.merchant_id == merchant.id,
                RecoveryCase.order_id == order.id,
            )
        ).scalars().first()

        if case:
            return {
                "status": "success",
                "scenario": "demo_checkout_abandonment",
                "demo_run_id": run_id,
                "case_id": case.id,
                "case_status": str(case.status),
                "merchant_id": merchant.id,
                "customer_name": customer_name,
                "order_external_id": ext_order_id,
                "amount": str(order.amount_total),
                "currency": DEMO_CURRENCY,
                "recommended_action": case.recommended_action,
            }

    # 1. Customer
    customer = db.execute(
        select(Customer).where(
            Customer.merchant_id == merchant.id,
            Customer.external_id == ext_customer_id,
        )
    ).scalars().first()

    if customer is None:
        customer = Customer(
            merchant_id=merchant.id,
            external_id=ext_customer_id,
            name=customer_name,
            email=f"cart_{clean_suffix}@example.com",
        )
        db.add(customer)
        db.commit()

    # 2. Abandoned Order (2 days old, no payment created)
    if order is None:
        abandoned_time = datetime.now(tz=timezone.utc) - timedelta(days=2)
        order = Order(
            merchant_id=merchant.id,
            customer_id=customer.id,
            external_id=ext_order_id,
            amount_total=amount,
            currency=DEMO_CURRENCY,
            created_at=abandoned_time,
        )
        db.add(order)
        db.commit()

    # 3. Trigger pipeline for abandonment
    provider = MockDefaultProvider(behavior="success", provider_reference=f"cart_{clean_suffix}")
    case = process_recovery_pipeline(
        db=db,
        merchant_id=merchant.id,
        payment_id=None,
        order_id=order.id,
        customer_id=customer.id,
        trigger_reason="CHECKOUT_ABANDONMENT",
        provider=provider,
    )

    return {
        "status": "success",
        "scenario": "demo_checkout_abandonment",
        "demo_run_id": run_id,
        "case_id": case.id if case else None,
        "case_status": str(case.status) if case else None,
        "merchant_id": merchant.id,
        "customer_name": customer_name,
        "order_external_id": ext_order_id,
        "amount": str(amount),
        "currency": DEMO_CURRENCY,
        "recommended_action": case.recommended_action if case else None,
    }


@router.post("/demo/batch")
def seed_demo_showcase_batch(
    req: Optional[DemoBatchRequest] = None,
    batch_run_id: Optional[str] = Query(None),
    user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Create a representative deterministic showcase batch of recovery cases.

    Contains a realistic mixture across recovery outcomes:
    1. Authorization Stale ($249.00) -> VERIFYING
    2. Authorization Stale ($1,499.00) -> RECOVERED (via capture simulation)
    3. Payment Failure ($320.00) -> notify_customer_failure
    4. Checkout Abandonment ($780.00) -> send_cart_recovery_email
    5. Economically Unjustified ($47.00) -> NO_ACTION (Revenue at risk $47.00, net <= 0)
    6. Authorization Stale ($89.00) -> RECOVERED (via capture simulation)

    Idempotent and isolated by batch_run_id. Retains historical cases.
    """
    _check_demo_env_guard()

    input_batch_id = (req.batch_run_id if req and req.batch_run_id else None) or batch_run_id
    batch_id, clean_batch = _get_clean_run_id(input_batch_id)
    merchant_id = user.merchant_id if user and hasattr(user, "merchant_id") else settings.razorpay_merchant_id

    cases_created = []

    # 1. Authorization Stale -> VERIFYING ($249.00)
    run_1 = f"batch_{clean_batch}_1"
    res1 = seed_demo_recovery_scenario(req=DemoScenarioRequest(demo_run_id=run_1), user=user, db=db)
    cases_created.append({"run_id": run_1, "case_id": res1.get("case_id"), "scenario": "auth_stale_verifying"})

    # 2. Authorization Stale -> RECOVERED ($1,499.00)
    run_2 = f"batch_{clean_batch}_2"
    res2 = seed_demo_recovery_scenario(req=DemoScenarioRequest(demo_run_id=run_2), user=user, db=db)
    if res2.get("case_id"):
        simulate_demo_payment_capture(req=DemoCaptureRequest(case_id=res2["case_id"]), user=user, db=db)
    cases_created.append({"run_id": run_2, "case_id": res2.get("case_id"), "scenario": "auth_stale_recovered"})

    # 3. Payment Failure -> notify_customer_failure ($320.00)
    run_3 = f"batch_{clean_batch}_3"
    ext_cust_3 = f"cust_{run_3}"
    cust_3 = db.execute(select(Customer).where(Customer.merchant_id == merchant_id, Customer.external_id == ext_cust_3)).scalars().first()
    if cust_3 is None:
        cust_3 = Customer(merchant_id=merchant_id, external_id=ext_cust_3, name="Meridian Labs", email=f"{run_3}@example.com")
        db.add(cust_3)
        db.commit()

    ord_3 = db.execute(select(Order).where(Order.merchant_id == merchant_id, Order.external_id == f"ord_{run_3}")).scalars().first()
    if ord_3 is None:
        ord_3 = Order(merchant_id=merchant_id, customer_id=cust_3.id, external_id=f"ord_{run_3}", amount_total=Decimal("320.00"), currency="USD")
        db.add(ord_3)
        db.commit()

    pay_3 = db.execute(select(Payment).where(Payment.merchant_id == merchant_id, Payment.provider_payment_id == f"pay_{run_3}")).scalars().first()
    if pay_3 is None:
        pay_3 = Payment(merchant_id=merchant_id, customer_id=cust_3.id, order_id=ord_3.id, provider_payment_id=f"pay_{run_3}", amount=Decimal("320.00"), currency="USD", status="failed", provider_state="failed")
        db.add(pay_3)
        db.commit()

    case3 = db.execute(select(RecoveryCase).where(RecoveryCase.merchant_id == merchant_id, RecoveryCase.order_id == ord_3.id)).scalars().first()
    if case3 is None:
        case3 = process_recovery_pipeline(db=db, merchant_id=merchant_id, payment_id=pay_3.id, order_id=ord_3.id, customer_id=cust_3.id, trigger_reason="PAYMENT_FAILURE", provider=MockDefaultProvider())
    cases_created.append({"run_id": run_3, "case_id": case3.id if case3 else None, "scenario": "payment_failure_notify"})

    # 4. Checkout Abandonment -> send_cart_recovery_email ($780.00)
    run_4 = f"batch_{clean_batch}_4"
    res4 = seed_demo_checkout_abandonment_scenario(req=DemoScenarioRequest(demo_run_id=run_4), user=user, db=db)
    cases_created.append({"run_id": run_4, "case_id": res4.get("case_id"), "scenario": "checkout_abandonment"})

    # 5. Economically Unjustified -> NO_ACTION ($47.00)
    run_5 = f"batch_{clean_batch}_5"
    res5 = seed_demo_no_action_scenario(req=DemoScenarioRequest(demo_run_id=run_5), user=user, db=db)
    cases_created.append({"run_id": run_5, "case_id": res5.get("case_id"), "scenario": "economically_unjustified_no_action"})

    # 6. Authorization Stale -> RECOVERED ($89.00)
    run_6 = f"batch_{clean_batch}_6"
    res6 = seed_demo_recovery_scenario(req=DemoScenarioRequest(demo_run_id=run_6), user=user, db=db)
    if res6.get("case_id"):
        simulate_demo_payment_capture(req=DemoCaptureRequest(case_id=res6["case_id"]), user=user, db=db)
    cases_created.append({"run_id": run_6, "case_id": res6.get("case_id"), "scenario": "auth_stale_recovered_small"})

    return {
        "status": "success",
        "batch_run_id": batch_id,
        "total_cases_created": len(cases_created),
        "cases": cases_created,
    }
