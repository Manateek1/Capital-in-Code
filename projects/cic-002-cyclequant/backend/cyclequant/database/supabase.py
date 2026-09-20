from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

import httpx

from cyclequant.models import DecisionRecord, MarketDataBundle, OrderEvent


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _integrity_hash(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


class SupabaseDatabase:
    """Scoped REST repository for the scheduled writer only.

    The writer uses a publishable key plus a CycleQuant-only token enforced by
    RLS. Browser reads use the same publishable key without the writer token.
    """

    def __init__(
        self,
        url: str,
        publishable_key: str,
        write_token: str,
        *,
        timeout_seconds: float = 20.0,
        client: httpx.Client | None = None,
    ) -> None:
        if not url.startswith("https://"):
            raise ValueError("SUPABASE_URL must use HTTPS")
        if not publishable_key.strip():
            raise ValueError("SUPABASE_PUBLISHABLE_KEY cannot be empty")
        if not write_token.strip():
            raise ValueError("CYCLEQUANT_WRITE_TOKEN cannot be empty")
        self.url = url.rstrip("/")
        self._owns_client = client is None
        self.client = client or httpx.Client(timeout=timeout_seconds)
        self.headers = {
            "apikey": publishable_key,
            "Authorization": f"Bearer {publishable_key}",
            "x-cyclequant-write-token": write_token,
            "Content-Type": "application/json",
        }

    @property
    def description(self) -> str:
        return f"{self.url}/rest/v1 (scoped writer)"

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def initialize(self) -> None:
        self._request("GET", "cq_decisions", params={"select": "id", "limit": "1"})

    def save_market_snapshot(self, bundle: MarketDataBundle) -> str:
        payload = bundle.model_dump(mode="json")
        digest = _integrity_hash(payload)
        existing = self._select(
            "cq_market_snapshots",
            {"select": "id", "integrity_hash": f"eq.{digest}", "limit": "1"},
        )
        if existing:
            return str(existing[0]["id"])
        snapshot_id = uuid4().hex
        self._request(
            "POST",
            "cq_market_snapshots",
            payload={
                "id": snapshot_id,
                "as_of": bundle.as_of.isoformat(),
                "captured_at": datetime.now(UTC).isoformat(),
                "symbol": bundle.symbol,
                "spot_price": str(bundle.spot_price),
                "private_payload": payload,
                "integrity_hash": digest,
            },
            prefer="return=minimal",
        )
        return snapshot_id

    def get_market_snapshot(self, snapshot_id: str) -> MarketDataBundle | None:
        rows = self._select(
            "cq_market_snapshots",
            {"select": "private_payload,integrity_hash", "id": f"eq.{snapshot_id}", "limit": "1"},
        )
        if not rows:
            return None
        self._verify(rows[0]["private_payload"], rows[0]["integrity_hash"])
        return MarketDataBundle.model_validate(rows[0]["private_payload"])

    def latest_market_snapshot(self) -> tuple[str, MarketDataBundle] | None:
        rows = self._select(
            "cq_market_snapshots",
            {
                "select": "id,private_payload,integrity_hash",
                "order": "as_of.desc",
                "limit": "1",
            },
        )
        if not rows:
            return None
        row = rows[0]
        self._verify(row["private_payload"], row["integrity_hash"])
        return str(row["id"]), MarketDataBundle.model_validate(row["private_payload"])

    def create_decision(self, decision: DecisionRecord) -> None:
        payload = decision.model_dump(mode="json")
        self._request(
            "POST",
            "cq_decisions",
            payload={
                "id": decision.id,
                "decision_date": decision.decision_date.isoformat(),
                "created_at": decision.timestamp.isoformat(),
                "strategy_version": decision.strategy_version,
                "market_snapshot_id": decision.market_snapshot_id,
                "current_exposure": decision.current_exposure,
                "target_exposure": decision.target_exposure,
                "action": decision.action.value,
                "total_score": decision.signals.total_score,
                "confidence": decision.signals.confidence.value,
                "public_payload": payload,
                "private_payload": payload,
                "integrity_hash": _integrity_hash(payload),
                "is_published": True,
            },
            prefer="return=minimal",
        )

    def get_decision(self, decision_id: str) -> DecisionRecord | None:
        return self._get_decision({"id": f"eq.{decision_id}"})

    def get_decision_for_date(self, decision_date: date) -> DecisionRecord | None:
        return self._get_decision({"decision_date": f"eq.{decision_date.isoformat()}"})

    def _get_decision(self, filters: dict[str, str]) -> DecisionRecord | None:
        rows = self._select(
            "cq_decisions",
            {"select": "public_payload,integrity_hash", "limit": "1", **filters},
        )
        if not rows:
            return None
        self._verify(rows[0]["public_payload"], rows[0]["integrity_hash"])
        return DecisionRecord.model_validate(rows[0]["public_payload"])

    def list_decisions(self, limit: int = 100) -> list[DecisionRecord]:
        rows = self._select(
            "cq_decisions",
            {
                "select": "public_payload,integrity_hash",
                "order": "decision_date.desc",
                "limit": str(min(max(limit, 1), 1000)),
            },
        )
        decisions = []
        for row in rows:
            self._verify(row["public_payload"], row["integrity_hash"])
            decisions.append(DecisionRecord.model_validate(row["public_payload"]))
        return decisions

    def append_order_event(self, event: OrderEvent) -> None:
        payload = event.model_dump(mode="json")
        self._request(
            "POST",
            "cq_order_events",
            payload={
                "id": event.id,
                "decision_id": event.decision_id,
                "order_id": event.order_id,
                "event_type": event.event_type,
                "status": event.status.value,
                "occurred_at": event.occurred_at.isoformat(),
                "public_payload": payload,
                "private_payload": payload,
                "integrity_hash": _integrity_hash(payload),
                "is_published": True,
            },
            prefer="return=minimal",
        )

    def list_order_events(self, decision_id: str) -> list[OrderEvent]:
        rows = self._select(
            "cq_order_events",
            {
                "select": "public_payload,integrity_hash",
                "decision_id": f"eq.{decision_id}",
                "order": "occurred_at.asc",
            },
        )
        events = []
        for row in rows:
            self._verify(row["public_payload"], row["integrity_hash"])
            events.append(OrderEvent.model_validate(row["public_payload"]))
        return events

    def claim_idempotency_key(self, key: str, decision_date: date) -> bool:
        response = self._raw_request(
            "POST",
            "cq_idempotency_keys",
            payload={"key": key, "decision_date": decision_date.isoformat()},
            prefer="return=minimal",
        )
        if response.status_code == 409:
            return False
        response.raise_for_status()
        return True

    def idempotency_key_exists(self, key: str) -> bool:
        return bool(
            self._select(
                "cq_idempotency_keys",
                {"select": "key", "key": f"eq.{key}", "limit": "1"},
            )
        )

    def has_allocation_change_on(self, decision_date: date) -> bool:
        return bool(
            self._select(
                "cq_decisions",
                {
                    "select": "id",
                    "decision_date": f"eq.{decision_date.isoformat()}",
                    "action": "in.(BUY,SELL)",
                    "limit": "1",
                },
            )
        )

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
    ) -> None:
        self._request(
            "POST",
            "cq_performance_daily",
            params={"on_conflict": "as_of"},
            payload={
                "as_of": as_of.isoformat(),
                "cyclequant_value": str(cyclequant_value),
                "btc_buy_hold_value": str(btc_buy_hold_value),
                "cash_value": str(cash_value),
                "ma200_value": str(ma200_value) if ma200_value is not None else None,
                "btc_price": str(btc_price),
                "btc_exposure": btc_exposure,
                "created_at": datetime.now(UTC).isoformat(),
                "is_published": True,
            },
            prefer="resolution=merge-duplicates,return=minimal",
        )

    def list_performance(self) -> list[dict[str, Any]]:
        return self._select(
            "cq_performance_daily",
            {"select": "*", "order": "as_of.asc", "limit": "1000"},
        )

    def _select(self, table: str, params: dict[str, str]) -> list[dict[str, Any]]:
        response = self._request("GET", table, params=params)
        payload = response.json()
        if not isinstance(payload, list):
            raise RuntimeError(f"Supabase returned a non-list response for {table}")
        return payload

    def _request(
        self,
        method: str,
        table: str,
        *,
        params: dict[str, str] | None = None,
        payload: Any | None = None,
        prefer: str | None = None,
    ) -> httpx.Response:
        response = self._raw_request(
            method, table, params=params, payload=payload, prefer=prefer
        )
        response.raise_for_status()
        return response

    def _raw_request(
        self,
        method: str,
        table: str,
        *,
        params: dict[str, str] | None = None,
        payload: Any | None = None,
        prefer: str | None = None,
    ) -> httpx.Response:
        headers = self.headers.copy()
        if prefer:
            headers["Prefer"] = prefer
        return self.client.request(
            method,
            f"{self.url}/rest/v1/{table}",
            params=params,
            json=payload,
            headers=headers,
        )

    @staticmethod
    def _verify(payload: Any, expected: str) -> None:
        if _integrity_hash(payload) != expected:
            raise RuntimeError("Supabase audit record failed integrity validation")
