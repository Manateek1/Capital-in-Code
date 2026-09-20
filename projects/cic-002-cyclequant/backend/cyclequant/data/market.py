from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx

from cyclequant.data.base import DataSourceError, SourcePayload
from cyclequant.data.http import request_json
from cyclequant.models import MetricPoint, OHLCVBar


class CoinbaseMarketDataProvider:
    name = "coinbase_exchange"
    category = "market"
    required = True
    stale_after = timedelta(hours=36)
    base_url = "https://api.exchange.coinbase.com"

    def __init__(self, client: httpx.AsyncClient, retries: int = 3) -> None:
        self.client = client
        self.retries = retries

    async def fetch(self, as_of: datetime, history_days: int) -> SourcePayload:
        end = as_of.astimezone(UTC)
        start = end - timedelta(days=history_days)
        cursor = start
        bars_by_timestamp: dict[datetime, OHLCVBar] = {}

        while cursor < end:
            chunk_end = min(cursor + timedelta(days=280), end)
            data = await request_json(
                self.client,
                self.name,
                "GET",
                f"{self.base_url}/products/BTC-USD/candles",
                params={
                    "granularity": 86400,
                    "start": cursor.isoformat(),
                    "end": chunk_end.isoformat(),
                },
                headers={"User-Agent": "CycleQuant/0.1"},
                retries=self.retries,
            )
            if not isinstance(data, list):
                raise DataSourceError(self.name, "unexpected candle response")
            for row in data:
                if not isinstance(row, list) or len(row) < 6:
                    continue
                timestamp = datetime.fromtimestamp(int(row[0]), tz=UTC)
                # Coinbase includes the still-forming UTC daily candle. Using it
                # would make a morning run depend on partial future-of-day data.
                if timestamp + timedelta(days=1) > end:
                    continue
                bars_by_timestamp[timestamp] = OHLCVBar(
                    timestamp=timestamp,
                    low=Decimal(str(row[1])),
                    high=Decimal(str(row[2])),
                    open=Decimal(str(row[3])),
                    close=Decimal(str(row[4])),
                    volume=Decimal(str(row[5])),
                )
            cursor = chunk_end + timedelta(seconds=1)

        bars = sorted(bars_by_timestamp.values(), key=lambda bar: bar.timestamp)
        if len(bars) < 200:
            raise DataSourceError(self.name, f"only {len(bars)} daily bars returned")
        latest = bars[-1]
        return SourcePayload(
            source=self.name,
            category=self.category,
            required=self.required,
            observed_at=latest.timestamp,
            bars=bars,
            metrics={
                "spot_price": MetricPoint(
                    value=float(latest.close),
                    observed_at=latest.timestamp,
                    source=self.name,
                    unit="USD",
                )
            },
            metadata={"product": "BTC-USD", "granularity_seconds": 86400},
        )
