from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from cyclequant.database import Database
from cyclequant.indicators import IndicatorEngine
from cyclequant.models import (
    Action,
    Confidence,
    DecisionRecord,
    MarketDataBundle,
    SignalReading,
    SignalSnapshot,
    SourceHealth,
    SourceState,
)


def test_snapshot_round_trip_and_audit_immutability(tmp_path, daily_bars) -> None:
    database = Database(tmp_path / "cyclequant.db")
    database.initialize()
    bundle = MarketDataBundle(
        as_of=daily_bars[-1].timestamp,
        spot_price=daily_bars[-1].close,
        bars=daily_bars,
        sources=[
            SourceHealth(
                name="fixture",
                state=SourceState.FRESH,
                required=True,
                observed_at=daily_bars[-1].timestamp,
            )
        ],
        indicators=IndicatorEngine().compute(daily_bars),
    )
    snapshot_id = database.save_market_snapshot(bundle)
    assert database.get_market_snapshot(snapshot_id) == bundle

    reading = SignalReading(
        name="valuation",
        score=60,
        configured_weight=1,
        effective_weight=1,
        rationale="fixture",
    )
    decision = DecisionRecord(
        decision_date=daily_bars[-1].timestamp.date(),
        timestamp=datetime.now(UTC),
        market_snapshot_id=snapshot_id,
        btc_price=daily_bars[-1].close,
        portfolio_value=Decimal("1000"),
        current_exposure=50,
        target_exposure=50,
        signals=SignalSnapshot(
            components={"valuation": reading},
            total_score=60,
            confidence=Confidence.MEDIUM,
            coverage=1,
            dispersion=0,
        ),
        ai_news_summary="No material news.",
        action=Action.HOLD,
        reasoning="No allocation change.",
    )
    database.create_decision(decision)
    assert database.get_decision(decision.id) == decision

    with (
        pytest.raises(sqlite3.DatabaseError, match="immutable"),
        database.connect() as connection,
    ):
        connection.execute("UPDATE decisions SET target_exposure = 75 WHERE id = ?", (decision.id,))


def test_idempotency_key_can_only_be_claimed_once(tmp_path) -> None:
    database = Database(tmp_path / "cyclequant.db")
    database.initialize()
    today = datetime.now(UTC).date()
    assert database.claim_idempotency_key("cq-test", today)
    assert not database.claim_idempotency_key("cq-test", today)
