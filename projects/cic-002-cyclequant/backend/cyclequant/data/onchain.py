from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx

from cyclequant.data.base import DataSourceError, SourcePayload
from cyclequant.data.http import request_json
from cyclequant.models import MetricPoint


class CoinMetricsOnChainProvider:
    name = "coinmetrics_community"
    category = "onchain"
    required = False
    stale_after = timedelta(days=3)
    endpoint = "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"

    def __init__(self, client: httpx.AsyncClient, retries: int = 3) -> None:
        self.client = client
        self.retries = retries

    async def fetch(self, as_of: datetime, history_days: int) -> SourcePayload:
        start_time = as_of - timedelta(days=90)
        data = await request_json(
            self.client,
            self.name,
            "GET",
            self.endpoint,
            params={
                "assets": "btc",
                "metrics": "CapMVRVCur",
                "frequency": "1d",
                "start_time": start_time.date().isoformat(),
                "end_time": as_of.date().isoformat(),
                "page_size": 1000,
            },
            retries=self.retries,
        )
        rows = data.get("data", []) if isinstance(data, dict) else []
        usable = [row for row in rows if row.get("CapMVRVCur") not in (None, "")]
        if not usable:
            raise DataSourceError(self.name, "MVRV data unavailable")
        latest = usable[-1]
        observed_at = datetime.fromisoformat(str(latest["time"]).replace("Z", "+00:00")).astimezone(
            UTC
        )
        values = [float(row["CapMVRVCur"]) for row in usable[-30:]]
        return SourcePayload(
            source=self.name,
            category=self.category,
            observed_at=observed_at,
            metrics={
                "mvrv": MetricPoint(
                    value=values[-1],
                    observed_at=observed_at,
                    source=self.name,
                    unit="ratio",
                    metadata={"30d_average": sum(values) / len(values)},
                )
            },
        )
