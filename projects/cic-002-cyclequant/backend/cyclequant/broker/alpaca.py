from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from urllib.parse import urlparse

import httpx

from cyclequant.broker.base import CryptoFees
from cyclequant.constants import ALPACA_PAPER_BASE_URL, BTC_USD
from cyclequant.data.http import request_json
from cyclequant.models import (
    Action,
    BrokerAccountSnapshot,
    OrderResult,
    OrderStatus,
    TradeIntent,
)

ALPACA_STATUS_MAP = {
    "new": OrderStatus.ACCEPTED,
    "accepted": OrderStatus.ACCEPTED,
    "pending_new": OrderStatus.PENDING,
    "accepted_for_bidding": OrderStatus.PENDING,
    "partially_filled": OrderStatus.PARTIALLY_FILLED,
    "filled": OrderStatus.FILLED,
    "done_for_day": OrderStatus.CANCELED,
    "canceled": OrderStatus.CANCELED,
    "expired": OrderStatus.CANCELED,
    "replaced": OrderStatus.CANCELED,
    "rejected": OrderStatus.REJECTED,
    "suspended": OrderStatus.REJECTED,
}


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


class AlpacaPaperBroker:
    """Minimal Alpaca adapter with an immutable paper-endpoint allow-list."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        api_key_id: str,
        api_secret_key: str,
        base_url: str = ALPACA_PAPER_BASE_URL,
        retries: int = 3,
    ) -> None:
        normalized = base_url.rstrip("/")
        parsed = urlparse(normalized)
        if (
            normalized != ALPACA_PAPER_BASE_URL
            or parsed.scheme != "https"
            or parsed.hostname != "paper-api.alpaca.markets"
        ):
            raise ValueError("CycleQuant only permits Alpaca's paper-api endpoint")
        if not api_key_id or not api_secret_key:
            raise ValueError("Alpaca paper API credentials are required")
        self.client = client
        self.endpoint = normalized
        self.retries = retries
        self.btc_price: Decimal | None = None
        self.headers = {
            "APCA-API-KEY-ID": api_key_id,
            "APCA-API-SECRET-KEY": api_secret_key,
            "Content-Type": "application/json",
        }

    async def get_account(self) -> BrokerAccountSnapshot:
        payload = await request_json(
            self.client,
            "alpaca_paper_account",
            "GET",
            f"{self.endpoint}/v2/account",
            headers=self.headers,
            retries=self.retries,
        )
        return BrokerAccountSnapshot(
            account_id=str(payload["id"]),
            status=str(payload["status"]),
            currency=str(payload["currency"]),
            portfolio_value=Decimal(str(payload["portfolio_value"])),
            cash=Decimal(str(payload["cash"])),
            buying_power=Decimal(str(payload["buying_power"])),
            trading_blocked=bool(payload.get("trading_blocked", False)),
            account_blocked=bool(payload.get("account_blocked", False)),
            crypto_trading_enabled=not bool(payload.get("trade_suspended_by_user", False)),
            endpoint=self.endpoint,
        )

    async def get_btc_position_quantity(self) -> Decimal:
        payload = await request_json(
            self.client,
            "alpaca_paper_positions",
            "GET",
            f"{self.endpoint}/v2/positions",
            headers=self.headers,
            retries=self.retries,
        )
        if not isinstance(payload, list):
            raise ValueError("Alpaca positions response must be a list")
        for position in payload:
            symbol = str(position.get("symbol", "")).upper().replace("/", "")
            if symbol == "BTCUSD":
                if position.get("current_price"):
                    self.btc_price = Decimal(str(position["current_price"]))
                return Decimal(str(position.get("qty") or "0"))
        return Decimal("0")

    async def _fee_activities(self, activity_type: str) -> list[dict]:
        activities: list[dict] = []
        page_token: str | None = None
        while True:
            params = {"direction": "asc", "page_size": "100"}
            if page_token:
                params["page_token"] = page_token
            page = await request_json(
                self.client,
                f"alpaca_paper_{activity_type.lower()}_activities",
                "GET",
                f"{self.endpoint}/v2/account/activities/{activity_type}",
                params=params,
                headers=self.headers,
                retries=self.retries,
            )
            if not isinstance(page, list):
                raise ValueError("Alpaca fee activities response must be a list")
            activities.extend(page)
            if len(page) < 100:
                break
            next_token = str(page[-1].get("id") or "")
            if not next_token or next_token == page_token:
                raise ValueError("Alpaca fee activities pagination did not advance")
            page_token = next_token
        return activities

    async def get_crypto_fees(self) -> CryptoFees:
        btc_quantity = Decimal("0")
        usd_amount = Decimal("0")
        for activity in await self._fee_activities("CFEE"):
            symbol = str(activity.get("symbol", "")).upper().replace("/", "")
            if symbol == "BTCUSD":
                btc_quantity -= Decimal(str(activity.get("qty") or "0"))
        for activity in await self._fee_activities("FEE"):
            symbol = str(activity.get("symbol", "")).upper().replace("/", "")
            if symbol == "BTCUSD":
                usd_amount -= Decimal(str(activity.get("net_amount") or "0"))
        if btc_quantity < 0 or usd_amount < 0:
            raise ValueError("Alpaca crypto fee totals cannot be negative")
        return CryptoFees(btc_quantity=btc_quantity, usd_amount=usd_amount)

    async def submit_market_order(self, intent: TradeIntent) -> OrderResult:
        if intent.symbol != BTC_USD:
            raise ValueError("AlpacaPaperBroker only supports BTC/USD")
        body: dict[str, str] = {
            "symbol": BTC_USD,
            "side": "buy" if intent.action == Action.BUY else "sell",
            "type": "market",
            "time_in_force": "gtc",
            "client_order_id": intent.client_order_id,
        }
        if intent.action == Action.SELL and intent.quantity:
            body["qty"] = format(intent.quantity, "f")
        else:
            body["notional"] = format(intent.notional.quantize(Decimal("0.01")), "f")
        payload = await request_json(
            self.client,
            "alpaca_paper_order",
            "POST",
            f"{self.endpoint}/v2/orders",
            headers=self.headers,
            retries=self.retries,
            json=body,
        )
        return self._order_from_payload(payload, intent.action, intent.notional)

    async def get_order_by_client_id(self, client_order_id: str) -> OrderResult | None:
        response = await self.client.get(
            f"{self.endpoint}/v2/orders:by_client_order_id",
            params={"client_order_id": client_order_id},
            headers=self.headers,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        payload = response.json()
        side = Action.BUY if payload.get("side") == "buy" else Action.SELL
        return self._order_from_payload(payload, side, Decimal(str(payload.get("notional") or 0)))

    @staticmethod
    def _order_from_payload(
        payload: dict, action: Action, requested_notional: Decimal
    ) -> OrderResult:
        status = ALPACA_STATUS_MAP.get(str(payload.get("status")), OrderStatus.PENDING)
        return OrderResult(
            order_id=str(payload.get("id")) if payload.get("id") else None,
            client_order_id=str(payload.get("client_order_id")),
            status=status,
            action=action,
            symbol=str(payload.get("symbol", BTC_USD)).replace("BTCUSD", BTC_USD),
            requested_notional=requested_notional,
            filled_quantity=Decimal(str(payload.get("filled_qty") or 0)),
            filled_average_price=(
                Decimal(str(payload["filled_avg_price"]))
                if payload.get("filled_avg_price")
                else None
            ),
            submitted_at=_parse_datetime(payload.get("submitted_at")),
            raw=payload,
        )
