from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, List, Dict
import datetime

from app.db.models import Order, Payment


@dataclass
class ContributingPayment:
    payment_id: Optional[int]
    provider_payment_id: Optional[str]
    amount: Optional[Decimal]
    currency: Optional[str]
    provider_state: Optional[str]
    provider_event_id: Optional[str]
    provider_state_at: Optional[datetime.datetime]


@dataclass
class RevenueTruthResult:
    order_id: Optional[int]
    expected_amount: Optional[Decimal]
    captured_amount: Decimal
    currency: Optional[str]
    recoverable_amount: Optional[Decimal]
    resolution: str
    contributing_payments: List[ContributingPayment]
    notes: Optional[str] = None


def assess_order_revenue(db, order_id: Optional[int]) -> RevenueTruthResult:
    """Deterministic, side-effect-free assessment of order revenue.

    - Uses Order.amount_total as authoritative expected_amount.
    - Sums Payment.amount for payments where provider_state == 'captured'.
    - Honors currency consistency: if captured payments have currencies that
      differ from order.currency, resolution is 'currency_mismatch' and
      recoverable_amount is None.
    - Does not create or mutate any DB rows.
    """
    if order_id is None:
        return RevenueTruthResult(
            order_id=None,
            expected_amount=None,
            captured_amount=Decimal("0"),
            currency=None,
            recoverable_amount=None,
            resolution="no_order",
            contributing_payments=[],
            notes="no order_id provided",
        )

    order = db.get(Order, order_id)
    if order is None:
        return RevenueTruthResult(
            order_id=None,
            expected_amount=None,
            captured_amount=Decimal("0"),
            currency=None,
            recoverable_amount=None,
            resolution="no_order",
            contributing_payments=[],
            notes="order not found",
        )

    expected = order.amount_total
    order_currency = order.currency

    # collect payments for provenance
    payments_q = db.query(Payment).filter(Payment.order_id == order.id).all()
    contributing: List[ContributingPayment] = []
    captured_amount = Decimal("0")
    currency_mismatch = False

    for p in payments_q:
        amt = None
        try:
            if p.amount is not None:
                amt = Decimal(p.amount)
        except Exception:
            amt = None

        cp = ContributingPayment(
            payment_id=p.id,
            provider_payment_id=p.provider_payment_id,
            amount=amt,
            currency=p.currency,
            provider_state=p.provider_state,
            provider_event_id=p.provider_event_id,
            provider_state_at=p.provider_state_at,
        )
        contributing.append(cp)

        # captured payments contribute their amount
        if p.provider_state == "captured":
            # require currency match to include in captured_amount
            if p.currency != order_currency:
                currency_mismatch = True
            else:
                if amt is not None:
                    captured_amount += amt

    # Determine resolution and recoverable_amount
    if expected is None:
        # cannot compute recoverable amount without expected
        return RevenueTruthResult(
            order_id=order.id,
            expected_amount=None,
            captured_amount=captured_amount,
            currency=order_currency,
            recoverable_amount=None,
            resolution="unknown",
            contributing_payments=contributing,
            notes="order.amount_total missing",
        )

    # If any captured payment currency mismatches order, mark mismatch
    if currency_mismatch:
        return RevenueTruthResult(
            order_id=order.id,
            expected_amount=Decimal(expected),
            captured_amount=captured_amount,
            currency=order_currency,
            recoverable_amount=None,
            resolution="currency_mismatch",
            contributing_payments=contributing,
            notes="captured payment currency differs from order currency",
        )

    # Normal deterministic calculation
    expected_dec = Decimal(expected)
    recoverable = expected_dec - captured_amount
    if recoverable < Decimal("0"):
        recoverable = Decimal("0")

    # resolution: if expected known and currencies consistent -> 'complete'
    res = "complete"

    return RevenueTruthResult(
        order_id=order.id,
        expected_amount=expected_dec,
        captured_amount=captured_amount,
        currency=order_currency,
        recoverable_amount=recoverable,
        resolution=res,
        contributing_payments=contributing,
        notes=None,
    )
