"""Regression tests for robustness-window alignment."""

from __future__ import annotations

import pandas as pd

from src.returns import calculate_returns
from src.robustness import build_robustness_checks


def test_start_date_sensitivity_discards_each_windows_first_return() -> None:
    dates = pd.to_datetime(
        [
            "1999-12-31",
            "2000-01-03",
            "2000-01-04",
            "2000-01-05",
        ]
    )
    prices = pd.DataFrame(
        {
            "open": [100.0, 110.0, 111.0, 112.0],
            "close": [100.0, 110.0, 111.0, 112.0],
        },
        index=dates,
    )
    daily = calculate_returns(prices).daily

    checks = build_robustness_checks(
        daily,
        trading_days_per_year=252,
        transaction_cost_bps=1.0,
    )
    start_2000 = next(
        record
        for record in checks["start_date_sensitivity"]
        if record["period"] == "start_2000"
    )

    assert start_2000["start_date"] == "2000-01-04"
    assert start_2000["metrics"]["overnight"]["observations"] == 2
