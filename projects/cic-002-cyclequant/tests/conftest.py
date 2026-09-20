from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from cyclequant.models import OHLCVBar


@pytest.fixture
def daily_bars() -> list[OHLCVBar]:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    bars: list[OHLCVBar] = []
    for index in range(500):
        trend = Decimal("20000") + Decimal(index * 75)
        cycle = Decimal((index % 30) - 15) * Decimal("12")
        close = trend + cycle
        bars.append(
            OHLCVBar(
                timestamp=start + timedelta(days=index),
                open=close - Decimal("25"),
                high=close + Decimal("150"),
                low=close - Decimal("150"),
                close=close,
                volume=Decimal("1000") + index,
            )
        )
    return bars
