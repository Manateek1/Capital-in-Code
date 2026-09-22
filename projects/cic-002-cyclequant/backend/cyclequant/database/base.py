from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Protocol

from cyclequant.models import (
    DecisionRecord,
    MarketDataBundle,
    OrderEvent,
    PaperAccountSnapshot,
)


class Repository(Protocol):
    @property
    def description(self) -> str: ...

    def initialize(self) -> None: ...

    def save_market_snapshot(self, bundle: MarketDataBundle) -> str: ...

    def get_market_snapshot(self, snapshot_id: str) -> MarketDataBundle | None: ...

    def latest_market_snapshot(self) -> tuple[str, MarketDataBundle] | None: ...

    def create_decision(self, decision: DecisionRecord) -> None: ...

    def get_decision(self, decision_id: str) -> DecisionRecord | None: ...

    def get_decision_for_date(self, decision_date: date) -> DecisionRecord | None: ...

    def list_decisions(self, limit: int = 100, offset: int = 0) -> list[DecisionRecord]: ...

    def append_order_event(self, event: OrderEvent) -> None: ...

    def list_order_events(self, decision_id: str) -> list[OrderEvent]: ...

    def save_paper_account_snapshot(self, snapshot: PaperAccountSnapshot) -> None: ...

    def latest_paper_account_snapshot(self) -> PaperAccountSnapshot | None: ...

    def claim_idempotency_key(self, key: str, decision_date: date) -> bool: ...

    def idempotency_key_exists(self, key: str) -> bool: ...

    def has_allocation_change_on(self, decision_date: date) -> bool: ...

    def upsert_performance(
        self,
        *,
        as_of: date,
        cyclequant_value: Decimal,
        btc_buy_hold_value: Decimal,
        cash_value: Decimal,
        ma200_value: Decimal | None,
        btc_price: Decimal,
        btc_exposure: int,
    ) -> None: ...

    def list_performance(self) -> list[dict[str, Any]]: ...
