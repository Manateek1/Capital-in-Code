from __future__ import annotations

import math
import statistics
from datetime import date
from typing import NamedTuple

from cyclequant.models import OHLCVBar

BITCOIN_GENESIS_DATE = date(2009, 1, 3)


class PowerLawEstimate(NamedTuple):
    fair_value: float
    price_ratio: float
    residual_zscore: float


def expanding_power_law(bars: list[OHLCVBar], minimum_points: int = 365) -> PowerLawEstimate | None:
    """Fit log(price) ~ log(days since genesis) using bars available as of evaluation.

    This intentionally fits an expanding window supplied by the caller; it does
    not use fixed coefficients estimated with future observations.
    """
    if len(bars) < minimum_points:
        return None

    x_values: list[float] = []
    y_values: list[float] = []
    for bar in bars:
        days = (bar.timestamp.date() - BITCOIN_GENESIS_DATE).days
        price = float(bar.close)
        if days > 0 and price > 0:
            x_values.append(math.log(days))
            y_values.append(math.log(price))
    if len(x_values) < minimum_points:
        return None

    x_mean = statistics.fmean(x_values)
    y_mean = statistics.fmean(y_values)
    denominator = sum((x - x_mean) ** 2 for x in x_values)
    if denominator == 0:
        return None
    slope = (
        sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values, strict=True))
        / denominator
    )
    intercept = y_mean - slope * x_mean
    fitted = [intercept + slope * x for x in x_values]
    residuals = [actual - estimate for actual, estimate in zip(y_values, fitted, strict=True)]
    residual_std = statistics.stdev(residuals) if len(residuals) > 1 else 0.0

    fair_value = math.exp(fitted[-1])
    actual_price = math.exp(y_values[-1])
    zscore = residuals[-1] / residual_std if residual_std else 0.0
    return PowerLawEstimate(
        fair_value=fair_value,
        price_ratio=actual_price / fair_value,
        residual_zscore=zscore,
    )
