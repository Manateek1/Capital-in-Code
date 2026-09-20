from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx

from cyclequant.data.base import DataSourceError, SourcePayload
from cyclequant.data.http import request_json
from cyclequant.models import MetricPoint


class ConfiguredEtfFlowProvider:
    """Adapter for a user-selected reliable JSON ETF-flow feed.

    Expected JSON is either one object or a list of objects containing
    `date`/`observed_at` and `net_flow_usd`. No scraper is enabled by default.
    """

    name = "configured_etf_flows"
    category = "etf_flows"
    required = False
    stale_after = timedelta(days=4)

    def __init__(self, client: httpx.AsyncClient, url: str | None, retries: int = 3) -> None:
        self.client = client
        self.url = url
        self.retries = retries

    async def fetch(self, as_of: datetime, history_days: int) -> SourcePayload:
        if not self.url:
            raise DataSourceError(self.name, "CQ_ETF_FLOWS_URL is not configured")
        data = await request_json(self.client, self.name, "GET", self.url, retries=self.retries)
        rows = data if isinstance(data, list) else [data]
        usable: list[tuple[datetime, float]] = []
        for row in rows:
            if not isinstance(row, dict) or row.get("net_flow_usd") is None:
                continue
            date_value = row.get("observed_at") or row.get("date")
            if not date_value:
                continue
            parsed = datetime.fromisoformat(str(date_value).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            parsed = parsed.astimezone(UTC)
            if parsed <= as_of:
                usable.append((parsed, float(row["net_flow_usd"])))
        if not usable:
            raise DataSourceError(self.name, "no usable ETF flow records")
        usable.sort(key=lambda item: item[0])
        observed_at, latest_flow = usable[-1]
        rolling = usable[-5:]
        return SourcePayload(
            source=self.name,
            category=self.category,
            observed_at=observed_at,
            metrics={
                "spot_btc_etf_net_flow_usd": MetricPoint(
                    value=latest_flow,
                    observed_at=observed_at,
                    source=self.name,
                    unit="USD",
                    metadata={"five_session_sum": sum(value for _, value in rolling)},
                )
            },
        )
