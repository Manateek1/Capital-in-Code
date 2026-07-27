"""Return calculation and alignment checks for CIC-001."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

RECONSTRUCTION_TOLERANCE = 1e-12


class ReturnCalculationError(ValueError):
    """Raised when aligned returns cannot be calculated consistently."""


@dataclass(frozen=True)
class ReturnCalculation:
    """Aligned daily return data and its maximum identity error."""

    daily: pd.DataFrame
    maximum_reconstruction_error: float


def _growth_from_log_returns(log_returns: pd.Series) -> pd.Series:
    values = np.exp(log_returns.cumsum())
    return pd.Series(values, index=log_returns.index, dtype=float)


def calculate_returns(prices: pd.DataFrame) -> ReturnCalculation:
    """Calculate correctly aligned simple, log, and cumulative returns.

    For each trading date ``t``:

    - overnight = open(t) / close(t-1) - 1
    - intraday = close(t) / open(t) - 1
    - close-to-close = close(t) / close(t-1) - 1

    The first row is removed because it has no previous trading-day close.
    """

    if not {"open", "close"}.issubset(prices.columns):
        raise ReturnCalculationError("clean prices must contain open and close")
    if len(prices) < 2:
        raise ReturnCalculationError("at least two price rows are required")
    if not prices.index.is_monotonic_increasing or not prices.index.is_unique:
        raise ReturnCalculationError("price dates must be sorted and unique")

    if "previous_observation_valid" in prices.columns:
        previous_observation_valid = prices["previous_observation_valid"].astype(bool)
    else:
        previous_observation_valid = pd.Series(True, index=prices.index, dtype=bool)

    daily = prices.loc[:, ["open", "close"]].copy()
    daily["previous_close"] = daily["close"].shift(1)
    aligned_rows = daily["previous_close"].notna() & previous_observation_valid
    daily = daily.loc[aligned_rows].copy()
    if daily.empty:
        raise ReturnCalculationError("no returns remain after previous-close alignment")

    daily["overnight_return"] = daily["open"] / daily["previous_close"] - 1.0
    daily["intraday_return"] = daily["close"] / daily["open"] - 1.0
    daily["close_to_close_return"] = daily["close"] / daily["previous_close"] - 1.0
    daily["overnight_log_return"] = np.log(daily["open"] / daily["previous_close"])
    daily["intraday_log_return"] = np.log(daily["close"] / daily["open"])
    daily["close_to_close_log_return"] = np.log(
        daily["close"] / daily["previous_close"]
    )
    daily["reconstructed_close_to_close_return"] = (1.0 + daily["overnight_return"]) * (
        1.0 + daily["intraday_return"]
    ) - 1.0
    daily["reconstruction_error"] = (
        daily["reconstructed_close_to_close_return"] - daily["close_to_close_return"]
    )

    maximum_error = float(daily["reconstruction_error"].abs().max())
    if not np.isfinite(maximum_error):
        raise ReturnCalculationError("return reconstruction produced non-finite values")
    if maximum_error > RECONSTRUCTION_TOLERANCE:
        raise ReturnCalculationError(
            "overnight and intraday returns do not reconstruct close-to-close "
            f"returns within tolerance: maximum_error={maximum_error:.3e}"
        )

    daily["overnight_growth"] = _growth_from_log_returns(daily["overnight_log_return"])
    daily["intraday_growth"] = _growth_from_log_returns(daily["intraday_log_return"])
    daily["buy_and_hold_growth"] = _growth_from_log_returns(
        daily["close_to_close_log_return"]
    )
    daily["cumulative_overnight_return"] = daily["overnight_growth"] - 1.0
    daily["cumulative_intraday_return"] = daily["intraday_growth"] - 1.0
    daily["cumulative_buy_and_hold_return"] = daily["buy_and_hold_growth"] - 1.0

    if not np.isfinite(daily.select_dtypes(include="number").to_numpy()).all():
        raise ReturnCalculationError("return calculation produced non-finite values")

    return ReturnCalculation(
        daily=daily,
        maximum_reconstruction_error=maximum_error,
    )
