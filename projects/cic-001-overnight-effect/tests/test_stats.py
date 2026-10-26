"""Tests for annualization, risk adjustment, drawdown, and inference."""

from __future__ import annotations

import pandas as pd
import pytest

from src.stats import (
    annualized_return,
    annualized_volatility,
    build_inferential_tests,
    build_strategy_comparison,
    build_summary_statistics,
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


def test_risk_metrics_match_daily_return_formulas() -> None:
    returns = pd.Series([0.10, -0.05, 0.02])
    risk_free_rate = 0.04
    trading_days = 252
    daily_risk_free = (1 + risk_free_rate) ** (1 / trading_days) - 1

    assert annualized_volatility(returns, trading_days) == pytest.approx(
        returns.std(ddof=1) * trading_days**0.5
    )
    assert sharpe_ratio(returns, risk_free_rate, trading_days) == pytest.approx(
        (returns.mean() - daily_risk_free) / returns.std(ddof=1) * trading_days**0.5
    )
    assert annualized_return(returns, trading_days) == pytest.approx(
        (1 + compounded_return(returns)) ** (trading_days / len(returns)) - 1
    )


def test_missing_returns_are_omitted_but_infinite_returns_are_rejected() -> None:
    returns = pd.Series([0.01, float("nan"), 0.03])

    assert annualized_volatility(returns, 2) == pytest.approx(
        annualized_volatility(pd.Series([0.01, 0.03]), 2)
    )
    with pytest.raises(ValueError, match="non-finite"):
        sharpe_ratio(pd.Series([0.01, float("inf")]), 0.0, 252)


def test_insufficient_and_zero_volatility_cases_are_undefined() -> None:
    one_observation = pd.Series([0.03])
    constant_returns = pd.Series([0.01, 0.01])

    assert pd.isna(annualized_return(one_observation, 252))
    assert pd.isna(annualized_volatility(one_observation, 252))
    assert pd.isna(sharpe_ratio(one_observation, 0.0, 252))
    assert annualized_volatility(constant_returns, 252) == 0.0
    assert pd.isna(sharpe_ratio(constant_returns, 0.0, 252))


def test_strategy_comparison_ranks_sharpe_and_flags_relative_volatility() -> None:
    summary = pd.DataFrame(
        [
            {
                "component": "overnight",
                "observations": 3,
                "cumulative_return": 0.10,
                "annualized_return": 0.12,
                "standard_deviation_daily": 0.02,
                "annualized_volatility": 0.10,
                "sharpe_ratio": 0.80,
                "maximum_drawdown": -0.08,
                "positive_observations_pct": 66.7,
            },
            {
                "component": "intraday",
                "observations": 3,
                "cumulative_return": 0.02,
                "annualized_return": 0.04,
                "standard_deviation_daily": 0.03,
                "annualized_volatility": 0.15,
                "sharpe_ratio": 0.20,
                "maximum_drawdown": -0.12,
                "positive_observations_pct": 33.3,
            },
            {
                "component": "buy_and_hold",
                "observations": 3,
                "cumulative_return": 0.20,
                "annualized_return": 0.22,
                "standard_deviation_daily": 0.05,
                "annualized_volatility": 0.25,
                "sharpe_ratio": 0.60,
                "maximum_drawdown": -0.18,
                "positive_observations_pct": 66.7,
            },
        ]
    )

    comparison = build_strategy_comparison(
        summary,
        annual_risk_free_rate=0.0,
    ).set_index("component")

    assert comparison.loc["overnight", "risk_adjusted_rank"] == 1
    assert comparison.loc["buy_and_hold", "return_rank"] == 1
    assert comparison.loc[
        "overnight", "excess_annualized_return_vs_buy_and_hold"
    ] == pytest.approx(-0.10)
    assert comparison.loc["buy_and_hold", "volatility_rank"] == 3
    assert bool(comparison.loc["buy_and_hold", "high_return_high_volatility_flag"])
    assert not bool(comparison.loc["overnight", "high_return_high_volatility_flag"])
    assert not bool(comparison.loc["intraday", "high_return_high_volatility_flag"])
    assert comparison.loc["overnight", "annual_risk_free_rate"] == 0.0


def test_strategy_comparison_leaves_unrankable_samples_unranked() -> None:
    daily = pd.DataFrame(
        {
            "overnight_return": [0.01],
            "intraday_return": [0.0],
            "close_to_close_return": [0.01],
        }
    )
    summary = build_summary_statistics(
        daily,
        annual_risk_free_rate=0.0,
        trading_days_per_year=252,
    )

    comparison = build_strategy_comparison(
        summary,
        annual_risk_free_rate=0.0,
    )

    assert comparison["return_rank"].isna().all()
    assert comparison["risk_adjusted_rank"].isna().all()
    assert comparison["sharpe_status"].eq("insufficient_observations").all()
    assert not comparison["high_return_high_volatility_flag"].any()


def test_summary_uses_the_same_complete_dates_for_every_return_stream() -> None:
    daily = pd.DataFrame(
        {
            "overnight_return": [0.01, 0.02, 0.03],
            "intraday_return": [0.00, float("nan"), 0.01],
            "close_to_close_return": [0.01, 0.02, 0.04],
        }
    )

    summary = build_summary_statistics(
        daily,
        annual_risk_free_rate=0.0,
        trading_days_per_year=252,
    )
    comparison = build_strategy_comparison(
        summary,
        annual_risk_free_rate=0.0,
    )

    assert summary["observations"].tolist() == [2, 2, 2]
    assert comparison["observations"].tolist() == [2, 2, 2]


def test_benchmark_comparison_rejects_different_sample_sizes() -> None:
    summary = pd.DataFrame(
        [
            {
                "component": component,
                "observations": observations,
                "cumulative_return": 0.1,
                "annualized_return": 0.1,
                "standard_deviation_daily": 0.01,
                "annualized_volatility": 0.15,
                "sharpe_ratio": 0.5,
                "maximum_drawdown": -0.1,
                "positive_observations_pct": 50.0,
            }
            for component, observations in [
                ("overnight", 3),
                ("intraday", 3),
                ("buy_and_hold", 2),
            ]
        ]
    )

    with pytest.raises(ValueError, match="same observations"):
        build_strategy_comparison(summary, annual_risk_free_rate=0.0)


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
