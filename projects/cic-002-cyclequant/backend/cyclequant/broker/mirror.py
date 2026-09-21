from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from cyclequant.broker.base import PaperBroker
from cyclequant.config import Settings
from cyclequant.constants import ALPACA_PAPER_BASE_URL
from cyclequant.database import Repository
from cyclequant.models import DecisionRecord, OrderStatus, PaperAccountSnapshot


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
    exposure = (
        decision.target_exposure
        if decision.order_status == OrderStatus.FILLED
        else decision.current_exposure
    )
    managed_value = decision.portfolio_value
    managed_btc_value = (
        managed_value * Decimal(exposure) / Decimal("100")
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    managed_cash = max(managed_value - managed_btc_value, Decimal("0"))
    managed_quantity = (managed_btc_value / decision.btc_price).quantize(
        Decimal("0.00000001")
    )
    reconciliation_difference = abs(broker_quantity - managed_quantity) * decision.btc_price
    reconciliation_tolerance = max(Decimal("1.00"), managed_value * Decimal("0.005"))
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
        btc_price=decision.btc_price,
        btc_exposure=exposure,
        managed_btc_quantity=managed_quantity,
        managed_btc_value=managed_btc_value,
        position_reconciled=reconciliation_difference <= reconciliation_tolerance,
        latest_action=decision.action,
        latest_order_status=decision.order_status,
    )
    database.save_paper_account_snapshot(snapshot)
    return snapshot
