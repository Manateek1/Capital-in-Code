from __future__ import annotations

from datetime import datetime, timedelta
from typing import Protocol

from pydantic import BaseModel, Field

from cyclequant.models import MetricPoint, NewsItem, OHLCVBar


class DataSourceError(RuntimeError):
    def __init__(self, source: str, message: str) -> None:
        super().__init__(f"{source}: {message}")
        self.source = source
        self.message = message


class SourcePayload(BaseModel):
    source: str
    category: str
    observed_at: datetime
    required: bool = False
    metrics: dict[str, MetricPoint] = Field(default_factory=dict)
    bars: list[OHLCVBar] = Field(default_factory=list)
    news: list[NewsItem] = Field(default_factory=list)
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class DataProvider(Protocol):
    name: str
    category: str
    required: bool
    stale_after: timedelta

    async def fetch(self, as_of: datetime, history_days: int) -> SourcePayload: ...
