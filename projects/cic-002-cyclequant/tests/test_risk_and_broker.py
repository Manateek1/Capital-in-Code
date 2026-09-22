from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import httpx

from cyclequant.broker import AlpacaPaperBroker, OrderCoordinator, SimulatedPaperBroker
from cyclequant.config import Settings
from cyclequant.database import Database
from cyclequant.indicators import IndicatorEngine
from cyclequant.models import (
    Action,
    BrokerAccountSnapshot,
    MarketDataBundle,
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
                {"symbol": "BTC/USD", "qty": "0.00285828"},
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


async def test_order_coordinator_never_duplicates_submission(tmp_path, daily_bars) -> None:
    context = make_context(tmp_path, daily_bars)
    risk = RiskEngine().evaluate(context)
    broker = SimulatedPaperBroker(btc_price=Decimal("50000"))
    coordinator = OrderCoordinator(context.database, broker)

    first = await coordinator.submit(context.intent, risk)
    second = await coordinator.submit(context.intent, risk)

    assert first.order_id == second.order_id
    assert broker.submission_count == 1
