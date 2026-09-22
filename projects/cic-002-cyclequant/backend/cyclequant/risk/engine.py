from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from pydantic import BaseModel

from cyclequant.config import Settings
from cyclequant.constants import (
    ALLOWED_EXPOSURES,
    ALPACA_PAPER_BASE_URL,
    BTC_USD,
    STARTING_CAPITAL,
)
from cyclequant.database import Repository
from cyclequant.models import (
    Action,
    BrokerAccountSnapshot,
    MarketDataBundle,
    TradeIntent,
)


class RiskCheck(BaseModel):
    name: str
    passed: bool
    reason: str


class RiskEvaluation(BaseModel):
    approved: bool
    checks: list[RiskCheck]

    @property
    def failures(self) -> list[RiskCheck]:
        return [check for check in self.checks if not check.passed]


@dataclass(frozen=True)
class RiskContext:
    settings: Settings
    database: Repository
    intent: TradeIntent
    account: BrokerAccountSnapshot
    market: MarketDataBundle
    kill_switch_path: Path
    position_quantity: Decimal = Decimal("0")
    managed_position_quantity: Decimal = Decimal("0")
    strategy_portfolio_value: Decimal = STARTING_CAPITAL


class RiskEngine:
    def evaluate(self, context: RiskContext) -> RiskEvaluation:
        intent = context.intent
        account = context.account
        settings = context.settings
        current = intent.current_exposure
        target = intent.target_exposure

        checks = [
            RiskCheck(
                name="trading_enabled",
                passed=settings.trading_enabled,
                reason=(
                    "CQ_TRADING_ENABLED is true."
                    if settings.trading_enabled
                    else "CQ_TRADING_ENABLED=false blocks every order."
                ),
            ),
            RiskCheck(
                name="kill_switch",
                passed=not context.kill_switch_path.exists(),
                reason=(
                    "Kill switch is clear."
                    if not context.kill_switch_path.exists()
                    else f"Emergency kill switch exists at {context.kill_switch_path}."
                ),
            ),
            RiskCheck(
                name="paper_endpoint",
                passed=self._paper_endpoint_is_valid(settings, account),
                reason=f"Broker endpoint is {account.endpoint}.",
            ),
            RiskCheck(
                name="instrument",
                passed=intent.symbol == BTC_USD,
                reason=f"Requested instrument is {intent.symbol}; only {BTC_USD} is permitted.",
            ),
            RiskCheck(
                name="allocation_bounds",
                passed=current in ALLOWED_EXPOSURES and target in ALLOWED_EXPOSURES,
                reason=f"Allocation transition is {current}% to {target}%.",
            ),
            RiskCheck(
                name="no_shorting",
                passed=0 <= target <= 100,
                reason="Target exposure must remain between 0% and 100%.",
            ),
            RiskCheck(
                name="maximum_step",
                passed=abs(target - current) <= settings.max_allocation_step,
                reason=(
                    f"Allocation step is {abs(target - current)} percentage points; "
                    f"maximum is {settings.max_allocation_step}."
                ),
            ),
            RiskCheck(
                name="direction",
                passed=self._direction_is_valid(intent),
                reason="Order side must match the target allocation direction.",
            ),
            RiskCheck(
                name="positive_size",
                passed=intent.notional > 0,
                reason=f"Order notional is {intent.notional}.",
            ),
            RiskCheck(
                name="no_margin",
                passed=intent.action != Action.BUY or intent.notional <= account.cash,
                reason=(
                    f"Buy notional is {intent.notional}; available cash is {account.cash}."
                ),
            ),
            RiskCheck(
                name="managed_notional",
                passed=intent.notional
                <= (
                    context.strategy_portfolio_value
                    * Decimal(abs(target - current))
                    / Decimal("100")
                    + Decimal("0.01")
                ),
                reason=(
                    f"Order notional {intent.notional} must fit the isolated strategy "
                    f"ledger value {context.strategy_portfolio_value}."
                ),
            ),
            RiskCheck(
                name="sufficient_position",
                passed=(
                    intent.action != Action.SELL
                    or (
                        intent.quantity is not None
                        and intent.quantity > 0
                        and intent.quantity <= context.position_quantity
                    )
                ),
                reason=(
                    f"Sell quantity is {intent.quantity}; BTC position is "
                    f"{context.position_quantity}."
                ),
            ),
            RiskCheck(
                name="position_reconciled",
                passed=(
                    abs(context.position_quantity - context.managed_position_quantity)
                    * context.market.spot_price
                    <= max(
                        Decimal("1.00"),
                        context.strategy_portfolio_value * Decimal("0.005"),
                    )
                ),
                reason="Broker BTC position must match the isolated fill ledger.",
            ),
            RiskCheck(
                name="market_freshness",
                passed=context.market.required_data_is_fresh(),
                reason="All required market sources must be fresh.",
            ),
            RiskCheck(
                name="account_state",
                passed=self._account_is_expected(account),
                reason=(
                    f"Account status={account.status}, currency={account.currency}, "
                    f"trading_blocked={account.trading_blocked}."
                ),
            ),
            RiskCheck(
                name="daily_limit",
                passed=not context.database.has_allocation_change_on(intent.decision_date),
                reason="At most one allocation adjustment is permitted per UTC date.",
            ),
            RiskCheck(
                name="idempotency",
                passed=not context.database.idempotency_key_exists(intent.client_order_id),
                reason=f"Client order id is {intent.client_order_id}.",
            ),
        ]
        return RiskEvaluation(approved=all(check.passed for check in checks), checks=checks)

    @staticmethod
    def _paper_endpoint_is_valid(settings: Settings, account: BrokerAccountSnapshot) -> bool:
        if settings.broker_mode == "simulated":
            return account.endpoint == "simulated://paper"
        return (
            settings.broker_mode == "alpaca-paper"
            and settings.alpaca_base_url == ALPACA_PAPER_BASE_URL
            and account.endpoint == ALPACA_PAPER_BASE_URL
        )

    @staticmethod
    def _direction_is_valid(intent: TradeIntent) -> bool:
        if intent.action == Action.BUY:
            return intent.target_exposure > intent.current_exposure
        if intent.action == Action.SELL:
            return intent.target_exposure < intent.current_exposure
        return False

    @staticmethod
    def _account_is_expected(account: BrokerAccountSnapshot) -> bool:
        return (
            account.status.upper() == "ACTIVE"
            and account.currency.upper() == "USD"
            and not account.trading_blocked
            and not account.account_blocked
            and account.crypto_trading_enabled
            and account.portfolio_value > 0
        )
