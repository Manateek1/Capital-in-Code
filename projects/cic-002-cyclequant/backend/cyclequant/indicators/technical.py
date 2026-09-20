from __future__ import annotations

import math
import statistics
from collections.abc import Sequence
from itertools import pairwise


def simple_moving_average(values: Sequence[float], window: int) -> float | None:
    if window <= 0:
        raise ValueError("window must be positive")
    if len(values) < window:
        return None
    return sum(values[-window:]) / window


def relative_strength_index(values: Sequence[float], period: int = 14) -> float | None:
    """Return Wilder's RSI using only observations supplied by the caller."""
    if period <= 0:
        raise ValueError("period must be positive")
    if len(values) <= period:
        return None

    deltas = [current - previous for previous, current in pairwise(values)]
    gains = [max(delta, 0.0) for delta in deltas]
    losses = [max(-delta, 0.0) for delta in deltas]

    average_gain = sum(gains[:period]) / period
    average_loss = sum(losses[:period]) / period
    for gain, loss in zip(gains[period:], losses[period:], strict=False):
        average_gain = ((average_gain * (period - 1)) + gain) / period
        average_loss = ((average_loss * (period - 1)) + loss) / period

    if average_loss == 0:
        return 100.0 if average_gain > 0 else 50.0
    relative_strength = average_gain / average_loss
    return 100.0 - (100.0 / (1.0 + relative_strength))


def realized_volatility(
    values: Sequence[float], window: int = 30, annualization_days: int = 365
) -> float | None:
    if window < 2:
        raise ValueError("window must be at least two")
    if len(values) < window + 1:
        return None
    sample = values[-(window + 1) :]
    log_returns = [math.log(current / previous) for previous, current in pairwise(sample)]
    return statistics.stdev(log_returns) * math.sqrt(annualization_days)


def drawdown_from_peak(values: Sequence[float], window: int | None = None) -> float | None:
    if not values:
        return None
    sample = values[-window:] if window else values
    peak = max(sample)
    return (sample[-1] / peak) - 1.0 if peak else None


def distance_from_average(value: float, average: float | None) -> float | None:
    if average in (None, 0):
        return None
    return (value / average) - 1.0
