from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal

import httpx

from cyclequant.broker import (
    AlpacaPaperBroker,
    OrderCoordinator,
    SimulatedPaperBroker,
    capture_paper_account,
    managed_ledger,
    resolve_decision_order_state,
)
from cyclequant.config import Settings
from cyclequant.database import Database
from cyclequant.indicators import IndicatorEngine
from cyclequant.models import (
    Action,
    BrokerAccountSnapshot,
    Confidence,
    DecisionRecord,
    MarketDataBundle,
    OrderEvent,
    OrderStatus,
    SignalReading,
    SignalSnapshot,
    SourceHealth,
    SourceState,
    TradeIntent,
)
from cyclequant.risk import RiskContext, RiskEngine


def make_market(daily_bars, state: SourceState = SourceState.FRESH) -> MarketDataBundle:
    return MarketDataBundle(
        as_of=daily_bars[-1].timestamp,
        spot_price=daily_bars[-1].close,
        bars=daily_bars,
        sources=[
            SourceHealth(
                name="market",
                state=state,
                required=True,
                observed_at=daily_bars[-1].timestamp,
            )
        ],
        indicators=IndicatorEngine().compute(daily_bars),
    )


def make_intent(day: date | None = None) -> TradeIntent:
    decision_date = day or datetime.now(UTC).date()
    return TradeIntent(
        decision_date=decision_date,
        action=Action.BUY,
        current_exposure=25,
        target_exposure=50,
        notional=Decimal("250"),
        client_order_id=f"cq-{decision_date:%Y%m%d}-50",
    )


def make_account(endpoint: str = "simulated://paper") -> BrokerAccountSnapshot:
    return BrokerAccountSnapshot(
        account_id="paper-test",
        status="ACTIVE",
        currency="USD",
        portfolio_value=Decimal("1000"),
        cash=Decimal("750"),
        buying_power=Decimal("750"),
        endpoint=endpoint,
    )


def make_context(tmp_path, daily_bars, **setting_overrides) -> RiskContext:
    database = Database(tmp_path / "cyclequant.db")
    database.initialize()
    settings = Settings(
        _env_file=None,
        trading_enabled=True,
        broker_mode="simulated",
        **setting_overrides,
    )
    return RiskContext(
        settings=settings,
        database=database,
        intent=make_intent(),
        account=make_account(),
        market=make_market(daily_bars),
        kill_switch_path=tmp_path / "KILL_SWITCH",
    )


def test_safe_simulated_paper_context_is_approved(tmp_path, daily_bars) -> None:
    evaluation = RiskEngine().evaluate(make_context(tmp_path, daily_bars))
    assert evaluation.approved
    assert all(check.passed for check in evaluation.checks)


def test_disabled_trading_and_stale_data_are_blocking(tmp_path, daily_bars) -> None:
    context = make_context(tmp_path, daily_bars)
    context.settings.trading_enabled = False
    context.market.sources[0].state = SourceState.STALE
    evaluation = RiskEngine().evaluate(context)
    failed = {check.name for check in evaluation.failures}
    assert {"trading_enabled", "market_freshness"} <= failed


def test_kill_switch_and_duplicate_key_are_blocking(tmp_path, daily_bars) -> None:
    context = make_context(tmp_path, daily_bars)
    context.kill_switch_path.write_text("STOP", encoding="utf-8")
    assert context.database.claim_idempotency_key(
        context.intent.client_order_id, context.intent.decision_date
    )
    evaluation = RiskEngine().evaluate(context)
    failed = {check.name for check in evaluation.failures}
    assert {"kill_switch", "idempotency"} <= failed


def test_unexpected_account_state_is_rejected(tmp_path, daily_bars) -> None:
    context = make_context(tmp_path, daily_bars)
    context.account.trading_blocked = True
    evaluation = RiskEngine().evaluate(context)
    assert "account_state" in {check.name for check in evaluation.failures}


def test_order_cannot_scale_to_brokers_headline_balance(tmp_path, daily_bars) -> None:
    context = make_context(tmp_path, daily_bars)
    context.account.cash = Decimal("100000")
    context.account.portfolio_value = Decimal("100000")
    context.intent.notional = Decimal("25000")
    evaluation = RiskEngine().evaluate(context)
    assert "managed_notional" in {check.name for check in evaluation.failures}


def test_untracked_broker_btc_blocks_new_order(tmp_path, daily_bars) -> None:
    context = replace(
        make_context(tmp_path, daily_bars),
        position_quantity=Decimal("0.00001"),
    )
    evaluation = RiskEngine().evaluate(context)
    assert "position_reconciled" in {check.name for check in evaluation.failures}


async def test_alpaca_adapter_rejects_live_or_lookalike_hosts_async() -> None:
    async with httpx.AsyncClient() as client:
        for url in (
            "https://api.alpaca.markets",
            "http://paper-api.alpaca.markets",
            "https://paper-api.alpaca.markets.evil.example",
        ):
            try:
                AlpacaPaperBroker(
                    client,
                    api_key_id="test",
                    api_secret_key="test",
                    base_url=url,
                )
            except ValueError as exc:
                assert "paper-api" in str(exc)
            else:
                raise AssertionError(f"unsafe URL was accepted: {url}")


async def test_alpaca_adapter_reads_btc_from_positions_list() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/positions"
        return httpx.Response(
            200,
            json=[
                {"symbol": "ETH/USD", "qty": "0.25"},
                {"symbol": "BTC/USD", "qty": "0.00285828", "current_price": "86000"},
            ],
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        broker = AlpacaPaperBroker(
            client,
            api_key_id="test",
            api_secret_key="test",
        )
        quantity = await broker.get_btc_position_quantity()

    assert quantity == Decimal("0.00285828")
    assert broker.btc_price == Decimal("86000")


async def test_public_mirror_uses_actual_fill_and_current_mark(tmp_path, daily_bars) -> None:
    database = Database(tmp_path / "cyclequant.db")
    database.initialize()
    snapshot_id = database.save_market_snapshot(make_market(daily_bars))
    filled_quantity = Decimal("0.002865445")
    fill_price = Decimal("85535.837013237")
    mark_price = Decimal("86000")
    decision = DecisionRecord(
        decision_date=daily_bars[-1].timestamp.date(),
        market_snapshot_id=snapshot_id,
        btc_price=Decimal("86595"),
        portfolio_value=Decimal("1000"),
        current_exposure=0,
        target_exposure=25,
        signals=SignalSnapshot(
            components={
                "valuation": SignalReading(
                    name="valuation",
                    score=70,
                    configured_weight=1,
                    effective_weight=1,
                    rationale="fixture",
                )
            },
            total_score=70,
            confidence=Confidence.HIGH,
            coverage=1,
            dispersion=0,
        ),
        ai_news_summary="Fixture",
        action=Action.BUY,
        reasoning="Fixture",
        order_status=OrderStatus.PENDING,
    )
    database.create_decision(decision)
    event = OrderEvent(
        decision_id=decision.id,
        event_type="broker_reconciliation",
        status=OrderStatus.FILLED,
        filled_quantity=filled_quantity,
        filled_average_price=fill_price,
    )
    database.append_order_event(event)
    broker = SimulatedPaperBroker(btc_price=mark_price)
    broker.btc_quantity = filled_quantity
    broker.cash = Decimal("1000") - filled_quantity * fill_price
    effective = resolve_decision_order_state(decision, [event])
    mirrored = await capture_paper_account(
        settings=Settings(_env_file=None),
        database=database,
        broker=broker,
        decision=effective,
    )

    assert mirrored.managed_btc_quantity == filled_quantity
    assert mirrored.strategy_cash == Decimal("754.90")
    assert mirrored.managed_btc_value == Decimal("246.43")
    assert mirrored.strategy_portfolio_value == Decimal("1001.33")
    assert mirrored.btc_price == mark_price
    assert mirrored.btc_exposure == 25
    assert mirrored.actual_btc_exposure == Decimal("24.61")
    assert mirrored.position_reconciled

    broker.btc_quantity += Decimal("0.00001")
    unmatched = await capture_paper_account(
        settings=Settings(_env_file=None),
        database=database,
        broker=broker,
        decision=effective,
    )
    assert not unmatched.position_reconciled

    class PagedDecisions:
        def __init__(self):
            self.event_lookups = 0

        def list_decisions(self, limit=100, offset=0):
            if offset == 0:
                return [decision.model_copy(update={"action": Action.HOLD})] * 1000
            if offset == 1000:
                return [decision]
            return []

        def list_order_events(self, decision_id):
            assert decision_id == decision.id
            self.event_lookups += 1
            return [event]

    paged = PagedDecisions()
    assert managed_ledger(paged, mark_price) == (
        Decimal("754.90"),
        filled_quantity,
        Decimal("246.43"),
        Decimal("1001.33"),
    )
    assert paged.event_lookups == 1


async def test_order_coordinator_never_duplicates_submission(tmp_path, daily_bars) -> None:
    context = make_context(tmp_path, daily_bars)
    risk = RiskEngine().evaluate(context)
    broker = SimulatedPaperBroker(btc_price=Decimal("50000"))
    coordinator = OrderCoordinator(context.database, broker)

    first = await coordinator.submit(context.intent, risk)
    second = await coordinator.submit(context.intent, risk)

    assert first.order_id == second.order_id
    assert broker.submission_count == 1
