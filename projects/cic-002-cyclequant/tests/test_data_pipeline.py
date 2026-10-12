from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import pytest

from cyclequant.data.aggregator import MarketDataPipeline
from cyclequant.data.base import SourcePayload
from cyclequant.data.market import CoinbaseMarketDataProvider
from cyclequant.models import Confidence, MetricPoint, OHLCVBar, SourceState
from cyclequant.signals import SignalEngine


class FakeProvider:
    def __init__(
        self,
        *,
        name: str,
        category: str,
        payload: SourcePayload | None,
        required: bool = False,
        stale_after: timedelta = timedelta(days=2),
    ) -> None:
        self.name = name
        self.category = category
        self.required = required
        self.stale_after = stale_after
        self.payload = payload

    async def fetch(self, as_of: datetime, history_days: int) -> SourcePayload:
        if self.payload is None:
            raise RuntimeError("offline")
        return self.payload


async def test_pipeline_isolates_optional_provider_failure(
    daily_bars: list[OHLCVBar],
) -> None:
    as_of = daily_bars[-1].timestamp + timedelta(hours=1)
    market_payload = SourcePayload(
        source="market",
        category="market",
        observed_at=daily_bars[-1].timestamp,
        required=True,
        bars=daily_bars,
        metrics={
            "spot_price": MetricPoint(
                value=float(daily_bars[-1].close),
                observed_at=daily_bars[-1].timestamp,
                source="market",
            )
        },
    )
    pipeline = MarketDataPipeline(
        [
            FakeProvider(name="market", category="market", payload=market_payload, required=True),
            FakeProvider(name="optional", category="macro", payload=None),
        ]
    )
    bundle = await pipeline.run(as_of, history_days=500)
    assert bundle.spot_price == daily_bars[-1].close
    assert bundle.required_data_is_fresh()
    states = {source.name: source.state for source in bundle.sources}
    assert states == {"market": SourceState.FRESH, "optional": SourceState.UNAVAILABLE}


async def test_pipeline_marks_old_required_data_stale(daily_bars: list[OHLCVBar]) -> None:
    as_of = daily_bars[-1].timestamp + timedelta(days=3)
    market_payload = SourcePayload(
        source="market",
        category="market",
        observed_at=daily_bars[-1].timestamp,
        required=True,
        bars=daily_bars,
        metrics={
            "spot_price": MetricPoint(
                value=float(daily_bars[-1].close),
                observed_at=daily_bars[-1].timestamp,
                source="market",
            )
        },
    )
    pipeline = MarketDataPipeline(
        [
            FakeProvider(
                name="market",
                category="market",
                payload=market_payload,
                required=True,
                stale_after=timedelta(hours=36),
            )
        ]
    )
    bundle = await pipeline.run(as_of, history_days=500)
    assert bundle.sources[0].state == SourceState.STALE
    assert not bundle.required_data_is_fresh()


async def test_coinbase_provider_excludes_incomplete_daily_candle() -> None:
    as_of = datetime(2026, 9, 20, 6, tzinfo=UTC)
    rows = []
    for days_ago in range(201):
        timestamp = (as_of.replace(hour=0) - timedelta(days=days_ago)).timestamp()
        rows.append([timestamp, 99, 102, 100, 101, 1000])

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=rows)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        payload = await CoinbaseMarketDataProvider(client, retries=0).fetch(as_of, 250)

    assert len(payload.bars) == 200
    assert payload.bars[-1].timestamp.date() == (as_of - timedelta(days=1)).date()


@pytest.mark.parametrize("hour", [0, 6, 12, 13, 23])
async def test_coinbase_latest_completed_close_stays_fresh_all_day(hour: int) -> None:
    as_of = datetime(2026, 10, 9, hour, 41, tzinfo=UTC)
    midnight = as_of.replace(hour=0, minute=0)
    rows = [
        [(midnight - timedelta(days=days_ago)).timestamp(), 99, 102, 100, 101, 1000]
        for days_ago in range(501)
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        start = datetime.fromisoformat(request.url.params["start"]).timestamp()
        end = datetime.fromisoformat(request.url.params["end"]).timestamp()
        return httpx.Response(200, json=[row for row in rows if start <= row[0] <= end])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = CoinbaseMarketDataProvider(client, retries=0)
        payload = await provider.fetch(as_of, 500)
        bundle = await MarketDataPipeline([provider]).run(as_of, 500)

    # Candle timestamps remain bucket starts, but the closing price becomes
    # available at the bucket end. The current incomplete candle stays excluded.
    assert payload.bars[-1].timestamp == midnight - timedelta(days=1)
    assert payload.observed_at == midnight
    assert payload.metrics["spot_price"].observed_at == midnight
    assert bundle.sources[0].state == SourceState.FRESH
    assert bundle.required_data_is_fresh()
    assert SignalEngine().score(bundle, news_score=50).confidence != Confidence.LOW


async def test_coinbase_missing_latest_close_still_blocks_allocation() -> None:
    as_of = datetime(2026, 10, 9, 13, 41, tzinfo=UTC)
    midnight = as_of.replace(hour=0, minute=0)
    rows = [
        [(midnight - timedelta(days=days_ago)).timestamp(), 99, 102, 100, 101, 1000]
        for days_ago in range(2, 502)
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        start = datetime.fromisoformat(request.url.params["start"]).timestamp()
        end = datetime.fromisoformat(request.url.params["end"]).timestamp()
        return httpx.Response(200, json=[row for row in rows if start <= row[0] <= end])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = CoinbaseMarketDataProvider(client, retries=0)
        bundle = await MarketDataPipeline([provider]).run(as_of, 500)

    assert bundle.sources[0].state == SourceState.STALE
    assert not bundle.required_data_is_fresh()
    assert SignalEngine().score(bundle, news_score=50).confidence == Confidence.LOW
