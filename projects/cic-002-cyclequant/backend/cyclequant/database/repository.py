from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

from cyclequant.models import (
    DecisionRecord,
    MarketDataBundle,
    OrderEvent,
    PaperAccountSnapshot,
)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _integrity_hash(payload_json: str) -> str:
    return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


class Database:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    @property
    def description(self) -> str:
        return str(self.path)

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        schema_path = Path(__file__).with_name("schema.sql")
        with self.connect() as connection:
            connection.executescript(schema_path.read_text(encoding="utf-8"))

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=15.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA busy_timeout = 15000")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def save_market_snapshot(self, bundle: MarketDataBundle) -> str:
        snapshot_id = uuid4().hex
        payload_json = _canonical_json(bundle.model_dump(mode="json"))
        digest = _integrity_hash(payload_json)
        with self.connect() as connection:
            existing = connection.execute(
                "SELECT id FROM market_snapshots WHERE integrity_hash = ?", (digest,)
            ).fetchone()
            if existing:
                return str(existing["id"])
            connection.execute(
                """
                INSERT INTO market_snapshots(
                    id, as_of, captured_at, symbol, spot_price, payload_json, integrity_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot_id,
                    bundle.as_of.isoformat(),
                    datetime.now(UTC).isoformat(),
                    bundle.symbol,
                    str(bundle.spot_price),
                    payload_json,
                    digest,
                ),
            )
        return snapshot_id

    def get_market_snapshot(self, snapshot_id: str) -> MarketDataBundle | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT payload_json, integrity_hash FROM market_snapshots WHERE id = ?",
                (snapshot_id,),
            ).fetchone()
        if not row:
            return None
        if _integrity_hash(row["payload_json"]) != row["integrity_hash"]:
            raise RuntimeError(f"market snapshot {snapshot_id} failed integrity validation")
        return MarketDataBundle.model_validate_json(row["payload_json"])

    def latest_market_snapshot(self) -> tuple[str, MarketDataBundle] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT id, payload_json, integrity_hash
                FROM market_snapshots ORDER BY as_of DESC LIMIT 1
                """
            ).fetchone()
        if not row:
            return None
        if _integrity_hash(row["payload_json"]) != row["integrity_hash"]:
            raise RuntimeError(f"market snapshot {row['id']} failed integrity validation")
        return str(row["id"]), MarketDataBundle.model_validate_json(row["payload_json"])

    def create_decision(self, decision: DecisionRecord) -> None:
        payload_json = _canonical_json(decision.model_dump(mode="json"))
        digest = _integrity_hash(payload_json)
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT INTO decisions(
                    id, decision_date, created_at, strategy_version, market_snapshot_id,
                    current_exposure, target_exposure, action, total_score, confidence,
                    payload_json, integrity_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision.id,
                    decision.decision_date.isoformat(),
                    decision.timestamp.isoformat(),
                    decision.strategy_version,
                    decision.market_snapshot_id,
                    decision.current_exposure,
                    decision.target_exposure,
                    decision.action.value,
                    decision.signals.total_score,
                    decision.signals.confidence.value,
                    payload_json,
                    digest,
                ),
            )
            for name, signal in decision.signals.components.items():
                connection.execute(
                    """
                    INSERT INTO decision_signals(
                        decision_id, signal_name, score, configured_weight,
                        effective_weight, available, rationale, inputs_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        decision.id,
                        name,
                        signal.score,
                        signal.configured_weight,
                        signal.effective_weight,
                        int(signal.available),
                        signal.rationale,
                        _canonical_json(signal.inputs),
                    ),
                )

    def get_decision(self, decision_id: str) -> DecisionRecord | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT payload_json, integrity_hash FROM decisions WHERE id = ?",
                (decision_id,),
            ).fetchone()
        return self._decision_from_row(row) if row else None

    def get_decision_for_date(self, decision_date: date) -> DecisionRecord | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT payload_json, integrity_hash FROM decisions WHERE decision_date = ?",
                (decision_date.isoformat(),),
            ).fetchone()
        return self._decision_from_row(row) if row else None

    def list_decisions(self, limit: int = 100) -> list[DecisionRecord]:
        safe_limit = min(max(limit, 1), 1000)
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT payload_json, integrity_hash
                FROM decisions ORDER BY decision_date DESC LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
        return [self._decision_from_row(row) for row in rows]

    @staticmethod
    def _decision_from_row(row: sqlite3.Row) -> DecisionRecord:
        if _integrity_hash(row["payload_json"]) != row["integrity_hash"]:
            raise RuntimeError("decision record failed integrity validation")
        return DecisionRecord.model_validate_json(row["payload_json"])

    def append_order_event(self, event: OrderEvent) -> None:
        payload_json = _canonical_json(event.model_dump(mode="json"))
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO order_events(
                    id, decision_id, order_id, event_type, status, occurred_at,
                    payload_json, integrity_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.decision_id,
                    event.order_id,
                    event.event_type,
                    event.status.value,
                    event.occurred_at.isoformat(),
                    payload_json,
                    _integrity_hash(payload_json),
                ),
            )

    def list_order_events(self, decision_id: str) -> list[OrderEvent]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT payload_json, integrity_hash FROM order_events
                WHERE decision_id = ? ORDER BY occurred_at
                """,
                (decision_id,),
            ).fetchall()
        events: list[OrderEvent] = []
        for row in rows:
            if _integrity_hash(row["payload_json"]) != row["integrity_hash"]:
                raise RuntimeError("order event failed integrity validation")
            events.append(OrderEvent.model_validate_json(row["payload_json"]))
        return events

    def save_paper_account_snapshot(self, snapshot: PaperAccountSnapshot) -> None:
        payload_json = _canonical_json(snapshot.model_dump(mode="json"))
        digest = _integrity_hash(payload_json)
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO paper_account_snapshots(
                    id, captured_at, broker_mode, connected, payload_json, integrity_hash
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.id,
                    snapshot.captured_at.isoformat(),
                    snapshot.broker_mode,
                    int(snapshot.connected),
                    payload_json,
                    digest,
                ),
            )

    def latest_paper_account_snapshot(self) -> PaperAccountSnapshot | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT payload_json, integrity_hash
                FROM paper_account_snapshots
                ORDER BY captured_at DESC LIMIT 1
                """
            ).fetchone()
        if not row:
            return None
        if _integrity_hash(row["payload_json"]) != row["integrity_hash"]:
            raise RuntimeError("paper account snapshot failed integrity validation")
        return PaperAccountSnapshot.model_validate_json(row["payload_json"])

    def claim_idempotency_key(self, key: str, decision_date: date) -> bool:
        try:
            with self.connect() as connection:
                connection.execute(
                    "INSERT INTO idempotency_keys(key, decision_date, created_at) VALUES (?, ?, ?)",
                    (key, decision_date.isoformat(), datetime.now(UTC).isoformat()),
                )
            return True
        except sqlite3.IntegrityError:
            return False

    def idempotency_key_exists(self, key: str) -> bool:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM idempotency_keys WHERE key = ? LIMIT 1", (key,)
            ).fetchone()
        return row is not None

    def has_allocation_change_on(self, decision_date: date) -> bool:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT 1 FROM decisions
                WHERE decision_date = ? AND action IN ('BUY', 'SELL') LIMIT 1
                """,
                (decision_date.isoformat(),),
            ).fetchone()
        return row is not None

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
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO performance_daily(
                    as_of, cyclequant_value, btc_buy_hold_value, cash_value,
                    ma200_value, btc_price, btc_exposure, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(as_of) DO UPDATE SET
                    cyclequant_value = excluded.cyclequant_value,
                    btc_buy_hold_value = excluded.btc_buy_hold_value,
                    cash_value = excluded.cash_value,
                    ma200_value = excluded.ma200_value,
                    btc_price = excluded.btc_price,
                    btc_exposure = excluded.btc_exposure,
                    created_at = excluded.created_at
                """,
                (
                    as_of.isoformat(),
                    str(cyclequant_value),
                    str(btc_buy_hold_value),
                    str(cash_value),
                    str(ma200_value) if ma200_value is not None else None,
                    str(btc_price),
                    btc_exposure,
                    datetime.now(UTC).isoformat(),
                ),
            )

    def list_performance(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute("SELECT * FROM performance_daily ORDER BY as_of").fetchall()
        return [dict(row) for row in rows]
