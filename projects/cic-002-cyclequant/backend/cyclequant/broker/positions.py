from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from cyclequant.broker.coordinator import resolve_decision_order_state
from cyclequant.database import Repository
from cyclequant.models import Action, OrderStatus

# Alpaca charges at most 0.25% for spot market orders and posts fee activities
# at end of day: https://docs.alpaca.markets/us/docs/crypto-fees
MAX_CRYPTO_FEE_RATE = Decimal("0.0025")
FEE_POSTING_GRACE = timedelta(hours=36)
BTC_FEE_ROUNDING = Decimal("0.00000001")


@dataclass(frozen=True)
class PositionCheck:
    reconciled: bool
    pending_btc_fee_quantity: Decimal = Decimal("0")

    @property
    def trade_ready(self) -> bool:
        return self.reconciled or self.pending_btc_fee_quantity > 0


def check_position(
    database: Repository,
    *,
    broker_quantity: Decimal,
    ledger_quantity: Decimal,
    mark_price: Decimal,
    as_of: datetime,
) -> PositionCheck:
    """Verify a net position without waiting for delayed fee activities.

    Only a BTC shortfall within the documented maximum fee on recent filled
    BUYs qualifies. Extra BTC, larger shortfalls, and expired gaps still fail.
    The actual shortfall is used; the fee rate is a bound, not an assumed fee.
    """

    shortfall = ledger_quantity - broker_quantity
    if broker_quantity < 0 or ledger_quantity < 0:
        return PositionCheck(reconciled=False)
    if abs(shortfall) * mark_price <= Decimal("0.01"):
        return PositionCheck(reconciled=True)
    if shortfall <= 0:
        return PositionCheck(reconciled=False)

    fee_limit = Decimal("0")
    # Daily idempotency means a 36-hour window spans at most three records.
    # Include BUYs before a HOLD or SELL: their fee activity can still be late.
    for stored in database.list_decisions(limit=3):
        if stored.action != Action.BUY:
            continue
        if not timedelta(0) <= as_of - stored.timestamp <= FEE_POSTING_GRACE:
            continue
        decision = resolve_decision_order_state(stored, database.list_order_events(stored.id))
        if decision.order_status == OrderStatus.FILLED and decision.trade_quantity > 0:
            fee_limit += decision.trade_quantity * MAX_CRYPTO_FEE_RATE
    if fee_limit > 0 and shortfall <= fee_limit + BTC_FEE_ROUNDING:
        return PositionCheck(reconciled=False, pending_btc_fee_quantity=shortfall)
    return PositionCheck(reconciled=False)
