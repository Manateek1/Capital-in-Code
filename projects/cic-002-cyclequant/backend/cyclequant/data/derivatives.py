from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx

from cyclequant.data.base import DataSourceError, SourcePayload
from cyclequant.data.http import request_json
from cyclequant.models import MetricPoint


class BinanceFundingProvider:
    name = "binance_futures"
    category = "derivatives"
    required = False
    stale_after = timedelta(hours=24)
    endpoint = "https://fapi.binance.com/fapi/v1/fundingRate"

    def __init__(self, client: httpx.AsyncClient, retries: int = 3) -> None:
        self.client = client
        self.retries = retries

    async def fetch(self, as_of: datetime, history_days: int) -> SourcePayload:
        data = await request_json(
            self.client,
            self.name,
            "GET",
            self.endpoint,
            params={"symbol": "BTCUSDT", "limit": 30},
            retries=self.retries,
        )
        if not isinstance(data, list) or not data:
            raise DataSourceError(self.name, "funding response was empty")
        usable = [
            item for item in data if int(item["fundingTime"]) <= int(as_of.timestamp() * 1000)
        ]
        if not usable:
            raise DataSourceError(self.name, "no funding record at or before evaluation time")
        recent = usable[-21:]
        latest = recent[-1]
        observed_at = datetime.fromtimestamp(int(latest["fundingTime"]) / 1000, tz=UTC)
        latest_rate = float(latest["fundingRate"])
        average_rate = sum(float(item["fundingRate"]) for item in recent) / len(recent)
        return SourcePayload(
            source=self.name,
            category=self.category,
            observed_at=observed_at,
            metrics={
                "funding_rate": MetricPoint(
                    value=latest_rate,
                    observed_at=observed_at,
                    source=self.name,
                    unit="fraction_8h",
                ),
                "funding_rate_7d_average": MetricPoint(
                    value=average_rate,
                    observed_at=observed_at,
                    source=self.name,
                    unit="fraction_8h",
                ),
            },
        )
