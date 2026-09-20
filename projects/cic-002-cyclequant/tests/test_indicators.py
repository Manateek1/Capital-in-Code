from __future__ import annotations

import math

import pytest

from cyclequant.indicators import IndicatorEngine
from cyclequant.indicators.technical import (
    drawdown_from_peak,
    relative_strength_index,
    simple_moving_average,
)
from cyclequant.models import OHLCVBar


def test_basic_indicator_boundaries() -> None:
    assert simple_moving_average([1.0, 2.0], 3) is None
    assert simple_moving_average([1.0, 2.0, 3.0], 3) == 2.0
    assert relative_strength_index([1.0] * 15, 14) == 50.0
    assert drawdown_from_peak([100.0, 120.0, 90.0]) == pytest.approx(-0.25)


def test_indicator_snapshot_is_complete_for_long_history(daily_bars: list[OHLCVBar]) -> None:
    snapshot = IndicatorEngine().compute(daily_bars)
    assert snapshot.sma_20 is not None
    assert snapshot.sma_200 is not None
    assert snapshot.distance_from_sma_200 is not None
    assert 0 <= snapshot.rsi_14 <= 100
    assert snapshot.realized_volatility_30d is not None
    assert snapshot.drawdown_from_ath <= 0
    assert snapshot.power_law_fair_value is not None
    assert math.isfinite(snapshot.power_law_residual_zscore or 0)


def test_engine_does_not_use_bars_after_as_of(daily_bars: list[OHLCVBar]) -> None:
    cutoff = daily_bars[299].timestamp
    full_input = IndicatorEngine().compute(daily_bars, as_of=cutoff)
    truncated_input = IndicatorEngine().compute(daily_bars[:300], as_of=cutoff)
    assert full_input == truncated_input
