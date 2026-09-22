from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from fastapi.testclient import TestClient

from cyclequant.api import create_app
from cyclequant.broker import SimulatedPaperBroker
from cyclequant.config import Settings
from cyclequant.database import Database
from cyclequant.indicators import IndicatorEngine
from cyclequant.models import (
    Confidence,
    MarketDataBundle,
    OrderResult,
    OrderStatus,
    SignalReading,
    SignalSnapshot,
    SourceHealth,
    SourceState,
    TradeIntent,
)
from cyclequant.news_analysis import HeuristicNewsAnalyzer
from cyclequant.reporting import build_dashboard_payload
from cyclequant.strategy import DailyStrategyRunner


class FixedPipeline:
    def __init__(self, bundle: MarketDataBundle) -> None:
        self.bundle = bundle
        self.calls = 0

    async def run(self, as_of: datetime, history_days: int) -> MarketDataBundle:
        self.calls += 1
        return self.bundle.model_copy(update={"as_of": as_of})


class FixedSignalEngine:
    def score(self, market: MarketDataBundle, news_score: float | None = None) -> SignalSnapshot:
        components = {
            name: SignalReading(
                name=name,
                score=80,
                configured_weight=1 / 6,
                effective_weight=1 / 6,
                rationale="fixture",
            )
            for name in ("valuation", "trend", "drawdown", "onchain", "macro", "news")
        }
        return SignalSnapshot(
            components=components,
            total_score=70,
            confidence=Confidence.HIGH,
            coverage=1,
            dispersion=0,
        )


class DelayedFillBroker(SimulatedPaperBroker):
    async def submit_market_order(self, intent: TradeIntent) -> OrderResult:
        filled = await super().submit_market_order(intent)
        return filled.model_copy(
            update={
                "status": OrderStatus.PENDING,
                "filled_quantity": Decimal("0"),
                "filled_average_price": None,
            }
        )


async def test_daily_runner_is_idempotent_and_exports_audit_record(tmp_path, daily_bars) -> None:
    as_of = daily_bars[-1].timestamp
    bundle = MarketDataBundle(
        as_of=as_of,
        spot_price=daily_bars[-1].close,
        bars=daily_bars,
        sources=[
            SourceHealth(
                name="fixture",
                state=SourceState.FRESH,
                required=True,
                observed_at=as_of,
            )
        ],
        indicators=IndicatorEngine().compute(daily_bars, as_of=as_of),
    )
    database = Database(tmp_path / "cyclequant.db")
    database.initialize()
    pipeline = FixedPipeline(bundle)
    settings = Settings(
        _env_file=None,
        database_path=tmp_path / "cyclequant.db",
        kill_switch_path=tmp_path / "KILL_SWITCH",
        trading_enabled=False,
        confirmation_days=1,
    )
    runner = DailyStrategyRunner(
        settings=settings,
        database=database,
        pipeline=pipeline,
        news_analyzer=HeuristicNewsAnalyzer(),
        broker=SimulatedPaperBroker(btc_price=Decimal(str(bundle.spot_price))),
    )

    first = await runner.run(as_of)
    second = await runner.run(as_of)

    assert first.created
    assert not second.created
    assert second.decision.id == first.decision.id
    assert pipeline.calls == 1
    assert database.get_market_snapshot(first.decision.market_snapshot_id) is not None
    assert len(database.list_performance()) == 1
    account_snapshot = database.latest_paper_account_snapshot()
    assert account_snapshot is not None
    assert account_snapshot.paper_only
    assert account_snapshot.broker_mode == "simulated"
    assert not account_snapshot.connected
    assert account_snapshot.strategy_portfolio_value == Decimal("1000.00")

    app = create_app(settings, database)
    with TestClient(app) as client:
        health = client.get("/health")
        dashboard = client.get("/api/v1/dashboard")
        detail = client.get(f"/api/v1/decisions/{first.decision.id}")
        rejected_post = client.post("/api/v1/decisions", json={})

    assert health.status_code == 200
    assert dashboard.status_code == 200
    assert dashboard.json()["latest_decision"]["id"] == first.decision.id
    assert dashboard.json()["paper_account"]["id"] == account_snapshot.id
    assert "broker_btc_quantity" not in dashboard.json()["paper_account"]
    assert detail.status_code == 200
    assert detail.json()["market_snapshot"]["symbol"] == "BTC/USD"
    assert rejected_post.status_code == 405


async def test_runner_rebalances_against_actual_paper_position(tmp_path, daily_bars) -> None:
    as_of = daily_bars[-1].timestamp
    price = daily_bars[-1].close
    bundle = MarketDataBundle(
        as_of=as_of,
        spot_price=price,
        bars=daily_bars,
        sources=[
            SourceHealth(
                name="fixture",
                state=SourceState.FRESH,
                required=True,
                observed_at=as_of,
            )
        ],
        indicators=IndicatorEngine().compute(daily_bars, as_of=as_of),
    )
    database = Database(tmp_path / "cyclequant.db")
    database.initialize()
    settings = Settings(
        _env_file=None,
        database_path=tmp_path / "cyclequant.db",
        kill_switch_path=tmp_path / "KILL_SWITCH",
        trading_enabled=True,
        confirmation_days=1,
        initial_exposure=0,
    )
    # A broker account may have a much larger headline balance. CycleQuant must
    # still size only its isolated $1,000 research ledger.
    broker = DelayedFillBroker(starting_cash=Decimal("100000"), btc_price=price)
    result = await DailyStrategyRunner(
        settings=settings,
        database=database,
        pipeline=FixedPipeline(bundle),
        news_analyzer=HeuristicNewsAnalyzer(),
        broker=broker,
        signal_engine=FixedSignalEngine(),
    ).run(as_of)

    assert result.decision.current_exposure == 0
    assert result.decision.target_exposure == 25
    assert result.decision.portfolio_value == Decimal("1000.00")
    assert result.decision.trade_value == Decimal("250.00")
    assert result.decision.order_status.value == "FILLED"
    events = database.list_order_events(result.decision.id)
    assert [event.status for event in events] == [OrderStatus.PENDING, OrderStatus.FILLED]
    account_snapshot = database.latest_paper_account_snapshot()
    assert account_snapshot is not None
    assert account_snapshot.btc_exposure == 25
    assert account_snapshot.managed_btc_value == Decimal("250.00")
    assert account_snapshot.position_reconciled
    assert account_snapshot.latest_order_status == OrderStatus.FILLED
    dashboard = build_dashboard_payload(database)
    assert dashboard["latest_decision"]["order_status"] == "FILLED"
    assert dashboard["metrics"]["filled_trade_count"] == 1
