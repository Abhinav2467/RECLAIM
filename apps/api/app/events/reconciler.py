from decimal import Decimal
from typing import Optional

from sqlalchemy import select, or_
from sqlalchemy.exc import SQLAlchemyError
import datetime

from app.events.types import RevenueEvent, ReconciliationResult
from app.db.models import Payment, Order


def reconcile_revenue_event(db, event: RevenueEvent) -> ReconciliationResult:
    """Reconcile a normalized RevenueEvent against local Payment/Order state.

    Follows strict provider_event_id + timestamp ordering rules. Does not create
    missing Payments. Uses SELECT FOR UPDATE on Payment row when present.
    """
    # map event types to canonical provider states
    mapping = {
        "PAYMENT_AUTHORIZED": "authorized",
        "PAYMENT_FAILURE": "failed",
        "PAYMENT_CAPTURED": "captured",
    }

    # default result values
    payment_changed = False
    payment_prev_state = None
    payment_result_state = None
    payment_ignored = False
    payment_conflict = False
    conflict_reason = None

    order_prev = None
    order_result = None
    order_changed = False

    outcome = None

    try:
        # Special-case ORDER_PAID when payment_id absent: derive order state
        if event.event_type.name == "ORDER_PAID" and not event.payment_id:
            # derive order state from order_id presence
            if not event.order_id:
                # No payment_id and no order_id: cannot proceed
                outcome = "missing"
                return ReconciliationResult(
                    raw_event_id=event.raw_event_id,
                    provider_event_id=event.provider_event_id,
                    provider_observed_at=event.occurred_at,
                    provider_observed_confidence=event.occurred_at_source,
                    payment_id=None,
                    order_id=None,
                    payment_previous_state=None,
                    payment_resulting_state=None,
                    payment_changed=False,
                    payment_ignored=True,
                    payment_conflict=False,
                    conflict_reason=None,
                    order_previous_state=None,
                    order_resulting_state=None,
                    order_changed=False,
                    outcome="missing",
                    message="no payment_id or order_id provided",
                )

            # lookup order by merchant_id + external_id
            stmt_o = select(Order).where(
                Order.merchant_id == event.merchant_id,
                Order.external_id == event.order_id,
            )
            order_row = db.execute(stmt_o).scalars().one_or_none()
            if order_row is None:
                outcome = "missing"
                return ReconciliationResult(
                    raw_event_id=event.raw_event_id,
                    provider_event_id=event.provider_event_id,
                    provider_observed_at=event.occurred_at,
                    provider_observed_confidence=event.occurred_at_source,
                    payment_id=None,
                    order_id=event.order_id,
                    payment_previous_state=None,
                    payment_resulting_state=None,
                    payment_changed=False,
                    payment_ignored=True,
                    payment_conflict=False,
                    conflict_reason=None,
                    order_previous_state=None,
                    order_resulting_state=None,
                    order_changed=False,
                    outcome="missing",
                    message="order not found",
                )

            # compute derived order state BEFORE any mutations
            captured_stmt_before = select(Payment).where(
                Payment.order_id == order_row.id,
                or_(Payment.provider_state == "captured", Payment.status == "captured"),
            )
            captured_before = db.execute(captured_stmt_before).scalars().first()
            order_prev = "paid" if captured_before else "open"

            # We are not mutating any payments here; event only indicates order paid
            order_result = order_prev
            order_changed = False
            outcome = "derived"
            return ReconciliationResult(
                raw_event_id=event.raw_event_id,
                provider_event_id=event.provider_event_id,
                provider_observed_at=event.occurred_at,
                provider_observed_confidence=event.occurred_at_source,
                payment_id=None,
                order_id=event.order_id,
                payment_previous_state=None,
                payment_resulting_state=None,
                payment_changed=False,
                payment_ignored=False,
                payment_conflict=False,
                conflict_reason=None,
                order_previous_state=order_prev,
                order_resulting_state=order_result,
                order_changed=order_changed,
                outcome=outcome,
                message="derived order state from linked payments",
            )

        stmt = select(Payment).where(
            Payment.merchant_id == event.merchant_id,
            Payment.provider_payment_id == event.payment_id,
        ).with_for_update()
        row = db.execute(stmt).scalars().one_or_none()
        if row is None:
            outcome = "missing"
            return ReconciliationResult(
                raw_event_id=event.raw_event_id,
                provider_event_id=event.provider_event_id,
                provider_observed_at=event.occurred_at,
                provider_observed_confidence=event.occurred_at_source,
                payment_id=event.payment_id,
                order_id=event.order_id,
                payment_previous_state=None,
                payment_resulting_state=None,
                payment_changed=False,
                payment_ignored=True,
                payment_conflict=False,
                conflict_reason=None,
                order_previous_state=None,
                order_resulting_state=None,
                order_changed=False,
                outcome="missing",
                message="payment not found",
            )

        # found payment row; inspect stored provider fields
        payment_prev_state = row.provider_state or row.status
        stored_event_id = row.provider_event_id
        stored_ts = row.provider_state_at

        # determine incoming provider event id and timestamp
        incoming_event_id = event.provider_event_id or event.event_id
        incoming_ts = event.occurred_at

        # Determine target state from event type
        target = mapping.get(event.event_type.name)
        if target is None:
            outcome = "unsupported"
            return ReconciliationResult(
                raw_event_id=event.raw_event_id,
                provider_event_id=incoming_event_id,
                provider_observed_at=incoming_ts,
                provider_observed_confidence=event.occurred_at_source,
                payment_id=event.payment_id,
                order_id=event.order_id,
                payment_previous_state=payment_prev_state,
                payment_resulting_state=None,
                payment_changed=False,
                payment_ignored=True,
                payment_conflict=False,
                conflict_reason=None,
                order_previous_state=None,
                order_resulting_state=None,
                order_changed=False,
                outcome="unsupported",
                message=f"unsupported event type: {event.event_type}",
            )

        # If incoming provider_event_id matches stored -> duplicate
        if stored_event_id and incoming_event_id and stored_event_id == incoming_event_id:
            outcome = "duplicate"
            return ReconciliationResult(
                raw_event_id=event.raw_event_id,
                provider_event_id=incoming_event_id,
                provider_observed_at=incoming_ts,
                provider_observed_confidence=event.occurred_at_source,
                payment_id=event.payment_id,
                order_id=event.order_id,
                payment_previous_state=payment_prev_state,
                payment_resulting_state=payment_prev_state,
                payment_changed=False,
                payment_ignored=True,
                payment_conflict=False,
                conflict_reason=None,
                order_previous_state=None,
                order_resulting_state=None,
                order_changed=False,
                outcome="duplicate",
                message="event already processed",
            )

        # If incoming timestamp is missing -> cannot safely order
        if incoming_ts is None:
            outcome = "unordered"
            return ReconciliationResult(
                raw_event_id=event.raw_event_id,
                provider_event_id=incoming_event_id,
                provider_observed_at=None,
                provider_observed_confidence=None,
                payment_id=event.payment_id,
                order_id=event.order_id,
                payment_previous_state=payment_prev_state,
                payment_resulting_state=None,
                payment_changed=False,
                payment_ignored=True,
                payment_conflict=False,
                conflict_reason="incoming timestamp missing",
                order_previous_state=None,
                order_resulting_state=None,
                order_changed=False,
                outcome="unordered",
                message="incoming occurred_at missing; cannot determine ordering",
            )

        # Compare timestamps (stored_ts may be None)
        if stored_ts is not None:
            if incoming_ts < stored_ts:
                outcome = "stale"
                return ReconciliationResult(
                    raw_event_id=event.raw_event_id,
                    provider_event_id=incoming_event_id,
                    provider_observed_at=incoming_ts,
                    provider_observed_confidence=event.occurred_at_source,
                    payment_id=event.payment_id,
                    order_id=event.order_id,
                    payment_previous_state=payment_prev_state,
                    payment_resulting_state=payment_prev_state,
                    payment_changed=False,
                    payment_ignored=True,
                    payment_conflict=False,
                    conflict_reason="incoming older than stored",
                    order_previous_state=None,
                    order_resulting_state=None,
                    order_changed=False,
                    outcome="stale",
                    message="incoming event older than stored provider_state_at",
                )
            if incoming_ts == stored_ts and incoming_event_id != stored_event_id and target != (row.provider_state or row.status):
                outcome = "conflict"
                return ReconciliationResult(
                    raw_event_id=event.raw_event_id,
                    provider_event_id=incoming_event_id,
                    provider_observed_at=incoming_ts,
                    provider_observed_confidence=event.occurred_at_source,
                    payment_id=event.payment_id,
                    order_id=event.order_id,
                    payment_previous_state=payment_prev_state,
                    payment_resulting_state=payment_prev_state,
                    payment_changed=False,
                    payment_ignored=True,
                    payment_conflict=True,
                    conflict_reason="equal-timestamp-different-event",
                    order_previous_state=None,
                    order_resulting_state=None,
                    order_changed=False,
                    outcome="conflict",
                    message="equal timestamp but different event id/state",
                )

        # If we reach here, incoming_ts > stored_ts OR stored_ts is None: apply
        # Compute order_previous_state BEFORE mutating the payment
        if row.order_id:
            captured_stmt_before = select(Payment).where(
                Payment.order_id == row.order_id,
                Payment.provider_state == "captured",
            )
            captured_before = db.execute(captured_stmt_before).scalars().first()
            order_prev = "paid" if captured_before else "open"

        row.provider_state = target
        row.provider_state_at = incoming_ts
        row.provider_event_id = incoming_event_id
        row.provider_raw_event_id = event.raw_event_id
        row.provider_failure_code = event.failure_code
        row.provider_failure_reason = event.failure_reason
        db.add(row)
        payment_changed = True
        payment_result_state = target
        outcome = "applied"

        # Determine order_resulting_state AFTER mutation using same provider_state logic
        if row.order_id:
            # Prefer the just-applied state for the mutated payment to avoid read-after-write races
            if payment_result_state == "captured":
                captured_after = True
            else:
                captured_stmt_after = select(Payment).where(
                    Payment.order_id == row.order_id,
                    Payment.provider_state == "captured",
                )
                captured_after = db.execute(captured_stmt_after).scalars().first()
            order_result = "paid" if captured_after else "open"
            order_changed = (order_prev != order_result)

        db.commit()

    except SQLAlchemyError:
        db.rollback()
        raise

    return ReconciliationResult(
        raw_event_id=event.raw_event_id,
        provider_event_id=incoming_event_id,
        provider_observed_at=event.occurred_at,
        provider_observed_confidence=event.occurred_at_source,
        payment_id=event.payment_id,
        order_id=event.order_id,
        payment_previous_state=payment_prev_state,
        payment_resulting_state=payment_result_state,
        payment_changed=payment_changed,
        payment_ignored=payment_ignored,
        payment_conflict=payment_conflict,
        conflict_reason=conflict_reason,
        order_previous_state=order_prev,
        order_resulting_state=order_result,
        order_changed=order_changed,
        outcome=outcome,
        message=None,
    )
