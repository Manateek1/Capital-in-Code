"""Tests for annualization, risk adjustment, drawdown, and inference."""

from __future__ import annotations

import pandas as pd
import pytest

from src.stats import (
    annualized_return,
    annualized_volatility,
    build_inferential_tests,
    compounded_return,
    maximum_drawdown,
    sharpe_ratio,
)


def test_compounding_and_annualization() -> None:
    returns = pd.Series([0.10, 0.0])

    assert compounded_return(returns) == pytest.approx(0.10)
    assert annualized_return(returns, trading_days_per_year=2) == pytest.approx(0.10)


def test_annualized_volatility() -> None:
    returns = pd.Series([0.01, 0.03])

    assert annualized_volatility(returns, trading_days_per_year=2) == pytest.approx(
        0.02
    )


def test_sharpe_ratio_matches_manual_calculation() -> None:
    returns = pd.Series([0.01, 0.03])

    assert sharpe_ratio(
        returns,
        annual_risk_free_rate=0.0,
        trading_days_per_year=2,
    ) == pytest.approx(2.0)


def test_maximum_drawdown_matches_manual_calculation() -> None:
    returns = pd.Series([0.10, -0.20, 0.05])

    assert maximum_drawdown(returns) == pytest.approx(-0.20)


def test_paired_inference_is_reproducible() -> None:
    daily = pd.DataFrame(
        {
            "overnight_return": [0.01, 0.02, -0.01, 0.03, 0.01],
            "intraday_return": [0.00, -0.01, 0.01, 0.00, -0.02],
        }
    )

    first = build_inferential_tests(daily, bootstrap_samples=500, random_seed=7)
    second = build_inferential_tests(daily, bootstrap_samples=500, random_seed=7)

    pd.testing.assert_frame_equal(first, second)
    bootstrap = first.loc[first["test"] == "paired_bootstrap_mean_difference"].iloc[0]
    assert bootstrap["confidence_interval_lower"] <= bootstrap["estimate"]
    assert bootstrap["confidence_interval_upper"] >= bootstrap["estimate"]
