from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from cyclequant.models import BrokerAccountSnapshot, OrderResult, TradeIntent


@dataclass(frozen=True)
class CryptoFees:
    """Positive amounts charged by the broker to the managed BTC/USD sleeve."""

    btc_quantity: Decimal = Decimal("0")
    usd_amount: Decimal = Decimal("0")


class PaperBroker(Protocol):
    endpoint: str

    async def get_account(self) -> BrokerAccountSnapshot: ...

    async def get_btc_position_quantity(self) -> Decimal: ...

    async def get_crypto_fees(self) -> CryptoFees: ...

    async def submit_market_order(self, intent: TradeIntent) -> OrderResult: ...

    async def get_order_by_client_id(self, client_order_id: str) -> OrderResult | None: ...
