from __future__ import annotations

import asyncio
import csv
import io
from datetime import UTC, date, datetime, time, timedelta

import httpx

from cyclequant.data.base import DataSourceError, SourcePayload
from cyclequant.data.http import request
from cyclequant.models import MetricPoint

FRED_SERIES = {
    "fed_funds_rate": ("DFF", "percent"),
    "broad_dollar_index": ("DTWEXBGS", "index"),
    "fed_balance_sheet": ("WALCL", "millions_usd"),
}


class FredMacroProvider:
    name = "fred"
    category = "macro"
    required = False
    stale_after = timedelta(days=10)

    def __init__(self, client: httpx.AsyncClient, base_url: str, retries: int = 3) -> None:
        self.client = client
        self.base_url = base_url
        self.retries = retries

    async def _fetch_series(
        self, name: str, series_id: str, unit: str, start: date
    ) -> tuple[str, MetricPoint]:
        response = await request(
            self.client,
            self.name,
            "GET",
            self.base_url,
            params={"id": series_id, "cosd": start.isoformat()},
            retries=self.retries,
        )
        reader = csv.DictReader(io.StringIO(response.text))
        observations: list[tuple[date, float]] = []
        for row in reader:
            date_text = row.get("observation_date") or row.get("DATE")
            value_text = row.get(series_id)
            if not date_text or not value_text or value_text == ".":
                continue
            observations.append((date.fromisoformat(date_text), float(value_text)))
        if not observations:
            raise DataSourceError(self.name, f"no observations for {series_id}")
        observed_date, value = observations[-1]
        observed_at = datetime.combine(observed_date, time.min, tzinfo=UTC)
        metadata: dict[str, float | str] = {"series_id": series_id}
        if len(observations) >= 2:
            metadata["previous_value"] = observations[-2][1]
            metadata["change"] = value - observations[-2][1]
        return name, MetricPoint(
            value=value,
            observed_at=observed_at,
            source=self.name,
            unit=unit,
            metadata=metadata,
        )

    async def fetch(self, as_of: datetime, history_days: int) -> SourcePayload:
        start = (as_of - timedelta(days=min(history_days, 730))).date()
        results = await asyncio.gather(
            *(
                self._fetch_series(name, series_id, unit, start)
                for name, (series_id, unit) in FRED_SERIES.items()
            ),
            return_exceptions=True,
        )
        metrics: dict[str, MetricPoint] = {}
        errors: list[str] = []
        for result in results:
            if isinstance(result, Exception):
                errors.append(str(result))
            else:
                name, point = result
                metrics[name] = point
        if not metrics:
            raise DataSourceError(self.name, "; ".join(errors) or "all series unavailable")
        observed_at = max(point.observed_at for point in metrics.values())
        return SourcePayload(
            source=self.name,
            category=self.category,
            observed_at=observed_at,
            metrics=metrics,
            metadata={"partial_errors": " | ".join(errors) if errors else None},
        )
