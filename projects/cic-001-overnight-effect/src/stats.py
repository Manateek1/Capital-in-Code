"""Descriptive and inferential statistics for aligned return series."""

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import cast

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

RETURN_COLUMNS = {
    "overnight": "overnight_return",
    "intraday": "intraday_return",
    "buy_and_hold": "close_to_close_return",
}


def _clean_returns(returns: Iterable[float] | pd.Series) -> pd.Series:
    series = pd.Series(returns, dtype=float).dropna()
    if series.empty:
        raise ValueError("return series is empty")
    if not np.isfinite(series.to_numpy()).all():
        raise ValueError("return series contains non-finite values")
    if bool(series.le(-1.0).any()):
        raise ValueError("simple returns must be greater than -1.0")
    return series


def compounded_return(returns: Iterable[float] | pd.Series) -> float:
    """Return the compounded simple return using stable log summation."""

    series = _clean_returns(returns)
    return float(np.expm1(np.log1p(series.to_numpy()).sum()))


def geometric_mean_return(returns: Iterable[float] | pd.Series) -> float:
    """Return the per-observation geometric mean simple return."""

    series = _clean_returns(returns)
    return float(np.expm1(np.log1p(series.to_numpy()).mean()))


def annualized_return(
    returns: Iterable[float] | pd.Series,
    trading_days_per_year: int,
) -> float:
    """Annualize a compounded return from the observed daily series."""

    if trading_days_per_year <= 0:
        raise ValueError("trading days per year must be positive")
    series = _clean_returns(returns)
    return float(
        np.expm1(
            np.log1p(series.to_numpy()).sum() * trading_days_per_year / len(series)
        )
    )


def annualized_volatility(
    returns: Iterable[float] | pd.Series,
    trading_days_per_year: int,
) -> float:
    """Annualize sample standard deviation under square-root-of-time scaling."""

    if trading_days_per_year <= 0:
        raise ValueError("trading days per year must be positive")
    series = _clean_returns(returns)
    if len(series) < 2:
        return float("nan")
    return float(series.std(ddof=1) * math.sqrt(trading_days_per_year))


def sharpe_ratio(
    returns: Iterable[float] | pd.Series,
    annual_risk_free_rate: float,
    trading_days_per_year: int,
) -> float:
    """Calculate an arithmetic annualized Sharpe ratio from daily returns."""

    if annual_risk_free_rate <= -1.0:
        raise ValueError("annual risk-free rate must be greater than -1.0")
    series = _clean_returns(returns)
    if len(series) < 2:
        return float("nan")
    standard_deviation = float(series.std(ddof=1))
    if standard_deviation == 0.0:
        return float("nan")
    daily_risk_free_rate = (1.0 + annual_risk_free_rate) ** (
        1.0 / trading_days_per_year
    ) - 1.0
    return float(
        (series.mean() - daily_risk_free_rate)
        / standard_deviation
        * math.sqrt(trading_days_per_year)
    )


def maximum_drawdown(returns: Iterable[float] | pd.Series) -> float:
    """Return the most negative peak-to-trough decline of compounded wealth."""

    series = _clean_returns(returns)
    wealth = np.concatenate(([1.0], np.exp(np.log1p(series.to_numpy()).cumsum())))
    running_peak = np.maximum.accumulate(wealth)
    drawdowns = wealth / running_peak - 1.0
    return float(drawdowns.min())


def summarize_return_series(
    returns: Iterable[float] | pd.Series,
    *,
    component: str,
    annual_risk_free_rate: float,
    trading_days_per_year: int,
) -> dict[str, object]:
    """Calculate the complete descriptive-statistics record for one component."""

    series = _clean_returns(returns)
    quantiles = np.quantile(
        series.to_numpy(),
        [0.01, 0.05, 0.25, 0.75, 0.95, 0.99],
    )
    return {
        "component": component,
        "observations": len(series),
        "arithmetic_mean_daily": float(series.mean()),
        "geometric_mean_daily": geometric_mean_return(series),
        "median_daily": float(series.median()),
        "minimum_daily": float(series.min()),
        "maximum_daily": float(series.max()),
        "standard_deviation_daily": float(series.std(ddof=1)),
        "annualized_volatility": annualized_volatility(series, trading_days_per_year),
        "positive_observations_pct": float(series.gt(0.0).mean() * 100.0),
        "negative_observations_pct": float(series.lt(0.0).mean() * 100.0),
        "zero_observations_pct": float(series.eq(0.0).mean() * 100.0),
        "percentile_01": float(quantiles[0]),
        "percentile_05": float(quantiles[1]),
        "percentile_25": float(quantiles[2]),
        "percentile_75": float(quantiles[3]),
        "percentile_95": float(quantiles[4]),
        "percentile_99": float(quantiles[5]),
        "skewness": float(scipy_stats.skew(series.to_numpy(), bias=False)),
        "excess_kurtosis": float(
            scipy_stats.kurtosis(series.to_numpy(), fisher=True, bias=False)
        ),
        "cumulative_return": compounded_return(series),
        "annualized_return": annualized_return(series, trading_days_per_year),
        "sharpe_ratio": sharpe_ratio(
            series, annual_risk_free_rate, trading_days_per_year
        ),
        "maximum_drawdown": maximum_drawdown(series),
    }


def build_summary_statistics(
    daily: pd.DataFrame,
    *,
    annual_risk_free_rate: float,
    trading_days_per_year: int,
) -> pd.DataFrame:
    """Build overall statistics for overnight, intraday, and buy-and-hold."""

    records = [
        summarize_return_series(
            daily[column],
            component=component,
            annual_risk_free_rate=annual_risk_free_rate,
            trading_days_per_year=trading_days_per_year,
        )
        for component, column in RETURN_COLUMNS.items()
    ]
    return pd.DataFrame.from_records(records)


def build_component_comparison(summary: pd.DataFrame) -> pd.DataFrame:
    """Compare overnight statistics with the matching intraday statistics."""

    indexed = summary.set_index("component")
    overnight = indexed.loc["overnight"]
    intraday = indexed.loc["intraday"]
    record = {
        "comparison": "overnight_minus_intraday",
        "difference_mean_daily_return": (
            overnight["arithmetic_mean_daily"] - intraday["arithmetic_mean_daily"]
        ),
        "difference_median_daily_return": (
            overnight["median_daily"] - intraday["median_daily"]
        ),
        "difference_cumulative_return": (
            overnight["cumulative_return"] - intraday["cumulative_return"]
        ),
        "difference_annualized_volatility": (
            overnight["annualized_volatility"] - intraday["annualized_volatility"]
        ),
        "difference_sharpe_ratio": (
            overnight["sharpe_ratio"] - intraday["sharpe_ratio"]
        ),
    }
    return pd.DataFrame([record])


def _bootstrap_mean_difference(
    differences: np.ndarray,
    *,
    samples: int,
    seed: int,
    batch_size: int = 500,
) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    bootstrap_means = np.empty(samples, dtype=float)
    for start in range(0, samples, batch_size):
        stop = min(start + batch_size, samples)
        indices = rng.integers(
            low=0,
            high=len(differences),
            size=(stop - start, len(differences)),
        )
        bootstrap_means[start:stop] = differences[indices].mean(axis=1)
    lower, upper = np.quantile(bootstrap_means, [0.025, 0.975])
    return float(lower), float(upper)


def build_inferential_tests(
    daily: pd.DataFrame,
    *,
    bootstrap_samples: int,
    random_seed: int,
) -> pd.DataFrame:
    """Run paired tests and a paired bootstrap for daily component differences."""

    overnight = daily["overnight_return"].to_numpy(dtype=float)
    intraday = daily["intraday_return"].to_numpy(dtype=float)
    if len(overnight) != len(intraday) or len(overnight) < 2:
        raise ValueError("paired inferential analysis requires at least two rows")
    differences = overnight - intraday
    mean_difference = float(differences.mean())
    median_difference = float(np.median(differences))

    paired_t = scipy_stats.ttest_rel(overnight, intraday)
    standard_error = float(differences.std(ddof=1) / math.sqrt(len(differences)))
    t_critical = float(scipy_stats.t.ppf(0.975, df=max(len(differences) - 1, 1)))
    t_lower = mean_difference - t_critical * standard_error
    t_upper = mean_difference + t_critical * standard_error

    if bool(np.allclose(differences, 0.0)):
        wilcoxon_statistic, wilcoxon_p_value = 0.0, 1.0
    else:
        wilcoxon = scipy_stats.wilcoxon(
            overnight,
            intraday,
            alternative="two-sided",
            zero_method="wilcox",
        )
        wilcoxon_statistic = float(wilcoxon.statistic)
        wilcoxon_p_value = float(wilcoxon.pvalue)

    bootstrap_lower, bootstrap_upper = _bootstrap_mean_difference(
        differences,
        samples=bootstrap_samples,
        seed=random_seed,
    )

    records = [
        {
            "test": "paired_t_test",
            "estimate": mean_difference,
            "statistic": float(paired_t.statistic),
            "p_value": float(paired_t.pvalue),
            "confidence_level": 0.95,
            "confidence_interval_lower": t_lower,
            "confidence_interval_upper": t_upper,
            "assumption": (
                "Paired daily differences are independent over time and their "
                "sampling mean is approximately normal."
            ),
        },
        {
            "test": "wilcoxon_signed_rank",
            "estimate": median_difference,
            "statistic": wilcoxon_statistic,
            "p_value": wilcoxon_p_value,
            "confidence_level": float("nan"),
            "confidence_interval_lower": float("nan"),
            "confidence_interval_upper": float("nan"),
            "assumption": (
                "Paired differences are independent and approximately symmetric."
            ),
        },
        {
            "test": "paired_bootstrap_mean_difference",
            "estimate": mean_difference,
            "statistic": float("nan"),
            "p_value": float("nan"),
            "confidence_level": 0.95,
            "confidence_interval_lower": bootstrap_lower,
            "confidence_interval_upper": bootstrap_upper,
            "assumption": (
                "Trading dates are resampled as exchangeable pairs; serial "
                "dependence is not modeled."
            ),
        },
    ]
    return pd.DataFrame.from_records(records)


def build_yearly_statistics(
    daily: pd.DataFrame,
    *,
    annual_risk_free_rate: float,
    trading_days_per_year: int,
) -> pd.DataFrame:
    """Build tidy calendar-year statistics for each return component."""

    records: list[dict[str, object]] = []
    date_index = pd.DatetimeIndex(daily.index)
    for year, group in daily.groupby(date_index.year, sort=True):
        year_number = int(cast(int, year))
        for component, column in RETURN_COLUMNS.items():
            series = group[column]
            records.append(
                {
                    "year": year_number,
                    "component": component,
                    "observations": len(series),
                    "arithmetic_mean_daily": float(series.mean()),
                    "median_daily": float(series.median()),
                    "cumulative_return": compounded_return(series),
                    "annualized_return": annualized_return(
                        series, trading_days_per_year
                    ),
                    "annualized_volatility": annualized_volatility(
                        series, trading_days_per_year
                    ),
                    "positive_observations_pct": float(series.gt(0.0).mean() * 100.0),
                    "sharpe_ratio": sharpe_ratio(
                        series,
                        annual_risk_free_rate,
                        trading_days_per_year,
                    ),
                    "maximum_drawdown": maximum_drawdown(series),
                }
            )
    return pd.DataFrame.from_records(records)
