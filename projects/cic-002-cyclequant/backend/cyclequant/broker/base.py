from __future__ import annotations

from decimal import Decimal
from typing import Protocol

from cyclequant.models import BrokerAccountSnapshot, OrderResult, TradeIntent


class PaperBroker(Protocol):
    endpoint: str

    async def get_account(self) -> BrokerAccountSnapshot: ...

    async def get_btc_position_quantity(self) -> Decimal: ...

    async def submit_market_order(self, intent: TradeIntent) -> OrderResult: ...

    async def get_order_by_client_id(self, client_order_id: str) -> OrderResult | None: ...
