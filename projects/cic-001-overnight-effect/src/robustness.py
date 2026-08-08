"""Focused robustness checks for the overnight-effect comparison."""

from __future__ import annotations

from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from .stats import (
    annualized_return,
    annualized_volatility,
    compounded_return,
)

COMPONENTS = {
    "overnight": ("overnight_return", "overnight_log_return"),
    "intraday": ("intraday_return", "intraday_log_return"),
}


def _component_metrics(
    frame: pd.DataFrame,
    trading_days_per_year: int,
) -> dict[str, dict[str, float | int]]:
    metrics: dict[str, dict[str, float | int]] = {}
    for component, (simple_column, _) in COMPONENTS.items():
        returns = frame[simple_column]
        metrics[component] = {
            "observations": len(returns),
            "mean_daily_return": float(returns.mean()),
            "median_daily_return": float(returns.median()),
            "cumulative_return": compounded_return(returns),
            "annualized_return": annualized_return(returns, trading_days_per_year),
            "annualized_volatility": annualized_volatility(
                returns, trading_days_per_year
            ),
        }
    return metrics


def _period_record(
    name: str,
    frame: pd.DataFrame,
    trading_days_per_year: int,
) -> dict[str, Any] | None:
    if len(frame) < 2:
        return None
    return {
        "period": name,
        "start_date": frame.index.min().date().isoformat(),
        "end_date": frame.index.max().date().isoformat(),
        "metrics": _component_metrics(frame, trading_days_per_year),
    }


def _by_decade(
    daily: pd.DataFrame,
    trading_days_per_year: int,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    years = np.asarray(pd.DatetimeIndex(daily.index).year, dtype=int)
    decade_labels = (years // 10) * 10
    for decade in np.unique(decade_labels):
        frame = daily.iloc[np.flatnonzero(decade_labels == decade)]
        record = _period_record(
            f"{int(decade)}s",
            frame,
            trading_days_per_year,
        )
        if record is not None:
            records.append(record)
    return records


def _market_periods(
    daily: pd.DataFrame,
    trading_days_per_year: int,
) -> list[dict[str, Any]]:
    definitions = [
        ("pre_gfc", None, date(2007, 10, 8)),
        ("gfc_and_immediate_aftermath", date(2007, 10, 9), date(2009, 12, 31)),
        ("post_gfc_pre_covid", date(2010, 1, 1), date(2020, 2, 18)),
        ("covid_shock", date(2020, 2, 19), date(2020, 3, 23)),
        ("post_covid_shock", date(2020, 3, 24), None),
    ]
    records: list[dict[str, Any]] = []
    date_index = pd.DatetimeIndex(daily.index)
    for name, start, end in definitions:
        mask = np.ones(len(daily), dtype=bool)
        if start is not None:
            mask &= np.asarray(date_index >= pd.Timestamp(start), dtype=bool)
        if end is not None:
            mask &= np.asarray(date_index <= pd.Timestamp(end), dtype=bool)
        record = _period_record(
            name,
            daily.iloc[np.flatnonzero(mask)],
            trading_days_per_year,
        )
        if record is not None:
            records.append(record)
    return records


def _start_date_sensitivity(
    daily: pd.DataFrame,
    trading_days_per_year: int,
) -> list[dict[str, Any]]:
    candidates: list[tuple[str, date | None]] = [
        ("full_sample", None),
        ("start_2000", date(2000, 1, 1)),
        ("start_2010", date(2010, 1, 1)),
        ("start_2020", date(2020, 1, 1)),
    ]
    records: list[dict[str, Any]] = []
    date_index = pd.DatetimeIndex(daily.index)
    for name, start in candidates:
        if start is None:
            frame = daily
        else:
            mask = np.asarray(date_index >= pd.Timestamp(start), dtype=bool)
            frame = daily.iloc[np.flatnonzero(mask)]
            # Match a standalone run beginning on this date: its first price
            # observation has no in-window previous close and cannot form a return.
            frame = frame.iloc[1:]
        record = _period_record(name, frame, trading_days_per_year)
        if record is not None:
            records.append(record)
    return records


def _extreme_observation_check(
    daily: pd.DataFrame,
    trading_days_per_year: int,
) -> dict[str, Any]:
    columns = ["overnight_return", "intraday_return"]
    lower = daily[columns].quantile(0.01)
    upper = daily[columns].quantile(0.99)
    keep = daily[columns].ge(lower).all(axis=1) & daily[columns].le(upper).all(axis=1)
    trimmed = daily.loc[keep]
    return {
        "method": (
            "Paired dates are retained only when both component returns fall "
            "within their own full-sample 1st and 99th percentiles."
        ),
        "original_observations": len(daily),
        "retained_observations": len(trimmed),
        "removed_observations": int((~keep).sum()),
        "thresholds": {
            column: {
                "lower_01": float(lower.loc[column]),
                "upper_99": float(upper.loc[column]),
            }
            for column in columns
        },
        "metrics": _component_metrics(trimmed, trading_days_per_year),
    }


def _simple_versus_log(daily: pd.DataFrame) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for component, (simple_column, log_column) in COMPONENTS.items():
        simple = daily[simple_column]
        log_returns = daily[log_column]
        records.append(
            {
                "component": component,
                "mean_simple_daily": float(simple.mean()),
                "median_simple_daily": float(simple.median()),
                "mean_log_daily": float(log_returns.mean()),
                "median_log_daily": float(log_returns.median()),
                "sum_log_return": float(log_returns.sum()),
                "compounded_from_simple": compounded_return(simple),
                "compounded_from_log": float(np.expm1(log_returns.sum())),
            }
        )
    return records


def _transaction_cost_check(
    daily: pd.DataFrame,
    trading_days_per_year: int,
    transaction_cost_bps: float,
) -> dict[str, Any]:
    one_way_fraction = transaction_cost_bps / 10_000.0
    records: list[dict[str, Any]] = []
    for component, (simple_column, _) in COMPONENTS.items():
        gross = daily[simple_column]
        net = (1.0 + gross) * (1.0 - one_way_fraction) / (1.0 + one_way_fraction) - 1.0
        gross_cumulative = compounded_return(gross)
        net_cumulative = compounded_return(net)
        records.append(
            {
                "component": component,
                "gross_cumulative_return": gross_cumulative,
                "net_cumulative_return": net_cumulative,
                "cumulative_cost_drag": net_cumulative - gross_cumulative,
                "gross_annualized_return": annualized_return(
                    gross, trading_days_per_year
                ),
                "net_annualized_return": annualized_return(net, trading_days_per_year),
            }
        )
    return {
        "one_way_cost_basis_points": transaction_cost_bps,
        "round_trip_trade_legs_per_day": 2,
        "calculation": (
            "Each session assumes entry at price*(1+cost) and exit at "
            "price*(1-cost), compounded every observed trading day."
        ),
        "important_omissions": [
            "bid-ask spread variation",
            "market impact and slippage",
            "taxes",
            "execution failures",
            "financing and account constraints",
        ],
        "results": records,
    }


def build_robustness_checks(
    daily: pd.DataFrame,
    *,
    trading_days_per_year: int,
    transaction_cost_bps: float,
) -> dict[str, Any]:
    """Run a limited set of interpretable robustness analyses."""

    return {
        "decade_results": _by_decade(daily, trading_days_per_year),
        "major_market_period_results": _market_periods(daily, trading_days_per_year),
        "start_date_sensitivity": _start_date_sensitivity(daily, trading_days_per_year),
        "excluding_extreme_observations": _extreme_observation_check(
            daily, trading_days_per_year
        ),
        "simple_versus_log_returns": _simple_versus_log(daily),
        "transaction_cost_sensitivity": _transaction_cost_check(
            daily,
            trading_days_per_year,
            transaction_cost_bps,
        ),
        "interpretation_note": (
            "These checks describe historical sensitivity. They do not turn "
            "statistical significance into evidence of implementable profit."
        ),
    }
