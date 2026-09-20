from __future__ import annotations

from datetime import UTC, datetime

from cyclequant.indicators.cycle import halving_cycle_position
from cyclequant.indicators.technical import (
    distance_from_average,
    drawdown_from_peak,
    realized_volatility,
    relative_strength_index,
    simple_moving_average,
)
from cyclequant.indicators.valuation import expanding_power_law
from cyclequant.models import IndicatorSnapshot, OHLCVBar


class IndicatorEngine:
    def compute(self, bars: list[OHLCVBar], as_of: datetime | None = None) -> IndicatorSnapshot:
        if not bars:
            raise ValueError("at least one OHLCV bar is required")
        ordered = sorted(bars, key=lambda bar: bar.timestamp)
        evaluation_time = as_of or ordered[-1].timestamp
        if evaluation_time.tzinfo is None:
            evaluation_time = evaluation_time.replace(tzinfo=UTC)
        usable = [bar for bar in ordered if bar.timestamp <= evaluation_time]
        if not usable:
            raise ValueError("no OHLCV bars exist at or before the evaluation time")

        closes = [float(bar.close) for bar in usable]
        sma_20 = simple_moving_average(closes, 20)
        sma_50 = simple_moving_average(closes, 50)
        sma_100 = simple_moving_average(closes, 100)
        sma_200 = simple_moving_average(closes, 200)
        days_since_halving, cycle_fraction = halving_cycle_position(evaluation_time)
        power_law = expanding_power_law(usable)

        return IndicatorSnapshot(
            as_of=evaluation_time,
            sma_20=sma_20,
            sma_50=sma_50,
            sma_100=sma_100,
            sma_200=sma_200,
            distance_from_sma_200=distance_from_average(closes[-1], sma_200),
            rsi_14=relative_strength_index(closes, 14),
            realized_volatility_30d=realized_volatility(closes, 30),
            drawdown_from_ath=drawdown_from_peak(closes),
            drawdown_from_90d_high=drawdown_from_peak(closes, 90),
            days_since_halving=days_since_halving,
            halving_cycle_fraction=cycle_fraction,
            power_law_fair_value=power_law.fair_value if power_law else None,
            power_law_ratio=power_law.price_ratio if power_law else None,
            power_law_residual_zscore=power_law.residual_zscore if power_law else None,
        )
