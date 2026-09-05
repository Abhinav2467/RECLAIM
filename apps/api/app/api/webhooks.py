from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError
import json

from app.core.config import settings
from app.db.deps import get_db
from app.db.models import RawWebhookEvent, Merchant, Payment
from app.integrations.razorpay import verify_signature
from app.integrations.razorpay_normalizer import normalize_raw_webhook
from app.events.reconciler import reconcile_revenue_event
from app.events.types import RevenueEventParseError
from app.services.recovery_pipeline import process_recovery_pipeline
from sqlalchemy import select
import datetime

router = APIRouter()


@router.post("/razorpay")
async def razorpay_webhook(request: Request, db=Depends(get_db)):
    # Read raw bytes before any JSON parsing
    body = await request.body()

    # Headers (case-insensitive access)
    signature = request.headers.get("x-razorpay-signature")
    event_id = request.headers.get("x-razorpay-event-id")

    if not event_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing x-razorpay-event-id header")

    # Verify signature using configured secret
    secret = settings.razorpay_webhook_secret
    if not secret:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Webhook secret not configured")

    if not verify_signature(secret, body, signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    # Parse JSON payload after verification
    try:
        payload = json.loads(body.decode('utf-8'))
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed JSON payload")

    # Resolve single configured merchant deterministically from settings
    try:
        merchant_id = settings.razorpay_merchant_id
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="RAZORPAY_MERCHANT_ID not configured")

    merchant = db.get(Merchant, merchant_id)
    if merchant is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Configured merchant not found in DB")

    # Filter headers for persistence (exclude sensitive headers)
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ("authorization", "cookie", "set-cookie")}

    # Insert raw webhook event with ON CONFLICT DO NOTHING to be idempotent
    insert_stmt = pg_insert(RawWebhookEvent.__table__).values(
        merchant_id=merchant.id,
        provider="razorpay",
        provider_event_id=event_id,
        signature_header=signature,
        raw_body=body,
        payload=payload,
        headers=headers,
    ).on_conflict_do_nothing(constraint="uq_raw_webhook_events_merchant_provider_event")

    try:
        # Use RETURNING to reliably detect whether an insert actually occurred
        result = db.execute(insert_stmt.returning(RawWebhookEvent.id))
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")

    # If RETURNING produced no row, the INSERT was a no-op (duplicate)
    inserted_id = result.scalar_one_or_none()
    if inserted_id is None:
        return {"status": "duplicate"}

    # Retrieve the persisted raw event
    raw = db.get(RawWebhookEvent, inserted_id)

    # Process: normalize then reconcile. Keep raw insert committed; do not hold locks.
    try:
        rev = normalize_raw_webhook(raw.payload, raw.merchant_id, raw.provider, raw.id, provider_event_id=raw.provider_event_id)
    except RevenueEventParseError as e:
        raw.status = "failed"
        raw.error = str(e)
        raw.processed_at = datetime.datetime.now(tz=datetime.timezone.utc)
        db.add(raw)
        db.commit()
        return {"status": "failed", "provider_event_id": raw.provider_event_id, "error": str(e)}

    # Call reconciler (it manages its own transactions). It may raise; we catch to mark raw event failed.
    try:
        result = reconcile_revenue_event(db, rev)
    except Exception as e:
        # Reconciler should have rolled back its own transaction on error; mark raw event failed and persist error
        raw.status = "failed"
        raw.error = str(e)
        raw.processed_at = datetime.datetime.now(tz=datetime.timezone.utc)
        db.add(raw)
        db.commit()
        return {"status": "failed", "provider_event_id": raw.provider_event_id, "error": str(e)}

    # Success: mark raw event processed
    raw.status = "processed"
    raw.processed_at = datetime.datetime.now(tz=datetime.timezone.utc)
    raw.error = None
    db.add(raw)
    db.commit()

    # Trigger recovery pipeline for payment failure or captured verification
    recovery_case_id = None
    recovery_status = None
    if result.outcome == "applied" and result.payment_resulting_state in ("failed", "captured"):
        payment_row = None
        if result.payment_id:
            payment_row = db.execute(
                select(Payment).where(
                    Payment.merchant_id == raw.merchant_id,
                    Payment.provider_payment_id == result.payment_id,
                )
            ).scalars().first()

        if payment_row:
            trigger_reason = "PAYMENT_FAILURE" if result.payment_resulting_state == "failed" else "PAYMENT_CAPTURED"
            try:
                recovery_case = process_recovery_pipeline(
                    db=db,
                    merchant_id=raw.merchant_id,
                    payment_id=payment_row.id,
                    order_id=payment_row.order_id,
                    customer_id=payment_row.customer_id,
                    trigger_reason=trigger_reason,
                )
                if recovery_case:
                    recovery_case_id = recovery_case.id
                    recovery_status = str(recovery_case.status)
            except Exception:
                pass

    # Build structured response
    resp = {
        "status": "processed",
        "provider_event_id": raw.provider_event_id,
        "reconciliation": {
            "outcome": result.outcome,
            "payment_id": result.payment_id,
            "payment_previous_state": result.payment_previous_state,
            "payment_resulting_state": result.payment_resulting_state,
            "order_previous_state": result.order_previous_state,
            "order_resulting_state": result.order_resulting_state,
            "order_changed": result.order_changed,
        },
    }
    if recovery_case_id:
        resp["recovery_case_id"] = recovery_case_id
        resp["recovery_status"] = recovery_status
    return resp

