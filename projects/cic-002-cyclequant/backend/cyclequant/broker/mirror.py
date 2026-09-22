from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from cyclequant.broker.base import CryptoFees, PaperBroker
from cyclequant.broker.coordinator import resolve_decision_order_state
from cyclequant.config import Settings
from cyclequant.constants import ALPACA_PAPER_BASE_URL, STARTING_CAPITAL
from cyclequant.database import Repository
from cyclequant.models import Action, DecisionRecord, OrderStatus, PaperAccountSnapshot


def managed_ledger(
    database: Repository, mark_price: Decimal, fees: CryptoFees | None = None
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """Rebuild the isolated sleeve from immutable broker fills."""

    cash = STARTING_CAPITAL
    quantity = Decimal("0")
    offset = 0
    page_size = 1000
    while True:
        page = database.list_decisions(limit=page_size, offset=offset)
        for stored in page:
            if stored.action == Action.HOLD:
                continue
            decision = resolve_decision_order_state(
                stored, database.list_order_events(stored.id)
            )
            filled_quantity = decision.trade_quantity
            fill_price = decision.fill_price
            if filled_quantity <= 0 or fill_price is None:
                continue
            filled_value = filled_quantity * fill_price
            if decision.action == Action.BUY:
                cash -= filled_value
                quantity += filled_quantity
            elif decision.action == Action.SELL:
                cash += filled_value
                quantity -= filled_quantity
        if len(page) < page_size:
            break
        offset += len(page)

    if fees is not None:
        cash -= fees.usd_amount
        quantity -= fees.btc_quantity
    if cash < 0 or quantity < 0:
        raise RuntimeError("Managed fill ledger is negative; manual reconciliation required")
    cash = cash.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    btc_value = (quantity * mark_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    portfolio_value = cash + btc_value
    return cash, quantity, btc_value, portfolio_value


async def capture_paper_account(
    *,
    settings: Settings,
    database: Repository,
    broker: PaperBroker,
    decision: DecisionRecord,
) -> PaperAccountSnapshot:
    """Persist a sanitized broker check plus the isolated strategy sleeve.

    The broker's account identifier and headline balance are intentionally not
    published. CycleQuant exposes only its own managed sleeve and BTC position.
    """

    account = await broker.get_account()
    broker_quantity = await broker.get_btc_position_quantity()
    fees = await broker.get_crypto_fees()
    mark_price = Decimal(str(getattr(broker, "btc_price", None) or decision.btc_price))
    exposure = (
        decision.target_exposure
        if decision.order_status == OrderStatus.FILLED
        else decision.current_exposure
    )
    managed_cash, managed_quantity, managed_btc_value, managed_value = managed_ledger(
        database, mark_price, fees
    )
    actual_exposure = (
        managed_btc_value / managed_value * Decimal("100")
        if managed_value
        else Decimal("0")
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    reconciliation_difference = abs(broker_quantity - managed_quantity) * mark_price
    reconciliation_tolerance = Decimal("0.01")
    is_alpaca = account.endpoint == ALPACA_PAPER_BASE_URL
    snapshot = PaperAccountSnapshot(
        broker_mode="alpaca-paper" if is_alpaca else "simulated",
        connected=is_alpaca,
        account_status=account.status,
        currency=account.currency,
        trading_enabled=settings.trading_enabled and is_alpaca,
        trading_blocked=account.trading_blocked,
        account_blocked=account.account_blocked,
        crypto_trading_enabled=account.crypto_trading_enabled,
        strategy_portfolio_value=managed_value,
        strategy_cash=managed_cash,
        btc_price=mark_price,
        btc_exposure=exposure,
        actual_btc_exposure=actual_exposure,
        managed_btc_quantity=managed_quantity,
        managed_btc_value=managed_btc_value,
        btc_fee_quantity=fees.btc_quantity,
        usd_fees_paid=fees.usd_amount,
        position_reconciled=reconciliation_difference <= reconciliation_tolerance,
        latest_action=decision.action,
        latest_order_status=decision.order_status,
    )
    database.save_paper_account_snapshot(snapshot)
    return snapshot
