from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from cyclequant.broker.base import CryptoFees
from cyclequant.constants import BTC_USD, STARTING_CAPITAL
from cyclequant.models import (
    Action,
    BrokerAccountSnapshot,
    OrderResult,
    OrderStatus,
    TradeIntent,
)


class SimulatedPaperBroker:
    endpoint = "simulated://paper"

    def __init__(
        self,
        *,
        starting_cash: Decimal = STARTING_CAPITAL,
        btc_price: Decimal = Decimal("50000"),
    ) -> None:
        self.cash = starting_cash
        self.btc_quantity = Decimal("0")
        self.btc_price = btc_price
        self.orders: dict[str, OrderResult] = {}
        self.submission_count = 0

    async def get_account(self) -> BrokerAccountSnapshot:
        portfolio_value = self.cash + self.btc_quantity * self.btc_price
        return BrokerAccountSnapshot(
            account_id="cyclequant-simulated-paper",
            status="ACTIVE",
            currency="USD",
            portfolio_value=portfolio_value,
            cash=self.cash,
            buying_power=self.cash,
            endpoint=self.endpoint,
        )

    async def get_btc_position_quantity(self) -> Decimal:
        return self.btc_quantity

    async def get_crypto_fees(self) -> CryptoFees:
        return CryptoFees()

    async def submit_market_order(self, intent: TradeIntent) -> OrderResult:
        existing = self.orders.get(intent.client_order_id)
        if existing:
            return existing
        if intent.symbol != BTC_USD:
            raise ValueError("simulated paper broker only supports BTC/USD")
        if intent.action == Action.BUY:
            notional = min(intent.notional, self.cash)
            quantity = notional / self.btc_price
            self.cash -= notional
            self.btc_quantity += quantity
        elif intent.action == Action.SELL:
            quantity = min(intent.quantity or intent.notional / self.btc_price, self.btc_quantity)
            notional = quantity * self.btc_price
            self.btc_quantity -= quantity
            self.cash += notional
        else:
            raise ValueError("HOLD is not an order")
        self.submission_count += 1
        result = OrderResult(
            order_id=f"sim-{uuid4().hex[:12]}",
            client_order_id=intent.client_order_id,
            status=OrderStatus.FILLED,
            action=intent.action,
            symbol=intent.symbol,
            requested_notional=notional,
            filled_quantity=quantity,
            filled_average_price=self.btc_price,
            submitted_at=datetime.now(UTC),
            raw={"broker": "simulated-paper"},
        )
        self.orders[intent.client_order_id] = result
        return result

    async def get_order_by_client_id(self, client_order_id: str) -> OrderResult | None:
        return self.orders.get(client_order_id)
