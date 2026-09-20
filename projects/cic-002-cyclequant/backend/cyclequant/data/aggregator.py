from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from decimal import Decimal

import httpx

from cyclequant.config import Settings
from cyclequant.data.base import DataProvider, DataSourceError, SourcePayload
from cyclequant.data.derivatives import BinanceFundingProvider
from cyclequant.data.etf import ConfiguredEtfFlowProvider
from cyclequant.data.macro import FredMacroProvider
from cyclequant.data.market import CoinbaseMarketDataProvider
from cyclequant.data.news import GoogleNewsRssProvider
from cyclequant.data.onchain import CoinMetricsOnChainProvider
from cyclequant.indicators import IndicatorEngine
from cyclequant.models import MarketDataBundle, SourceHealth, SourceState

logger = logging.getLogger(__name__)


class MarketDataPipeline:
    def __init__(
        self,
        providers: list[DataProvider],
        indicator_engine: IndicatorEngine | None = None,
    ) -> None:
        if not any(provider.category == "market" and provider.required for provider in providers):
            raise ValueError("a required market provider is mandatory")
        self.providers = providers
        self.indicator_engine = indicator_engine or IndicatorEngine()

    async def _fetch_safe(
        self, provider: DataProvider, as_of: datetime, history_days: int
    ) -> SourcePayload | Exception:
        try:
            return await provider.fetch(as_of, history_days)
        except Exception as exc:  # provider isolation boundary
            logger.warning(
                "data source failed",
                extra={"source": provider.name, "category": provider.category, "error": str(exc)},
            )
            return exc

    async def run(self, as_of: datetime, history_days: int) -> MarketDataBundle:
        if as_of.tzinfo is None:
            as_of = as_of.replace(tzinfo=UTC)
        as_of = as_of.astimezone(UTC)
        results = await asyncio.gather(
            *(self._fetch_safe(provider, as_of, history_days) for provider in self.providers)
        )

        payloads: list[SourcePayload] = []
        health: list[SourceHealth] = []
        for provider, result in zip(self.providers, results, strict=True):
            if isinstance(result, Exception):
                health.append(
                    SourceHealth(
                        name=provider.name,
                        state=SourceState.UNAVAILABLE,
                        required=provider.required,
                        error=str(result),
                    )
                )
                continue
            payloads.append(result)
            age = as_of - result.observed_at
            state = SourceState.FRESH if age <= provider.stale_after else SourceState.STALE
            health.append(
                SourceHealth(
                    name=provider.name,
                    state=state,
                    required=provider.required,
                    observed_at=result.observed_at,
                    metadata=result.metadata,
                )
            )

        market = next((payload for payload in payloads if payload.category == "market"), None)
        if market is None or not market.bars or "spot_price" not in market.metrics:
            raise DataSourceError("market_pipeline", "required BTC market data unavailable")

        category_metrics: dict[str, dict] = {
            "macro": {},
            "derivatives": {},
            "onchain": {},
            "etf_flows": {},
        }
        news = []
        for payload in payloads:
            if payload.category in category_metrics:
                category_metrics[payload.category].update(payload.metrics)
            if payload.category == "news":
                news.extend(payload.news)

        indicators = self.indicator_engine.compute(market.bars, as_of=as_of)
        return MarketDataBundle(
            as_of=as_of,
            spot_price=Decimal(str(market.metrics["spot_price"].value)),
            bars=market.bars,
            macro=category_metrics["macro"],
            derivatives=category_metrics["derivatives"],
            onchain=category_metrics["onchain"],
            etf_flows=category_metrics["etf_flows"],
            news=sorted(news, key=lambda item: item.published_at, reverse=True),
            sources=health,
            indicators=indicators,
        )


def build_default_pipeline(settings: Settings, client: httpx.AsyncClient) -> MarketDataPipeline:
    providers: list[DataProvider] = [
        CoinbaseMarketDataProvider(client, retries=settings.request_retries),
        FredMacroProvider(client, settings.fred_csv_base_url, retries=settings.request_retries),
        CoinMetricsOnChainProvider(client, retries=settings.request_retries),
        BinanceFundingProvider(client, retries=settings.request_retries),
        ConfiguredEtfFlowProvider(client, settings.etf_flows_url, retries=settings.request_retries),
        GoogleNewsRssProvider(client, retries=settings.request_retries),
    ]
    return MarketDataPipeline(providers)


def build_http_client(settings: Settings) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(settings.request_timeout_seconds),
        follow_redirects=True,
        limits=httpx.Limits(max_connections=8, max_keepalive_connections=4),
    )
