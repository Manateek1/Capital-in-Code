"""Offline integration tests for generated files and chart artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.charts import generate_charts
from src.output import write_outputs
from src.returns import calculate_returns
from src.robustness import build_robustness_checks
from src.stats import (
    build_component_comparison,
    build_inferential_tests,
    build_summary_statistics,
    build_yearly_statistics,
)
from src.validation import ValidationReport


def _daily_sample() -> pd.DataFrame:
    dates = pd.bdate_range("2022-01-03", periods=520)
    overnight_factors = 1.0 + 0.0003 + 0.002 * np.sin(np.arange(520) / 13)
    intraday_factors = 1.0 - 0.0001 + 0.003 * np.cos(np.arange(520) / 17)
    opens = np.empty(520)
    closes = np.empty(520)
    previous_close = 100.0
    for index in range(520):
        opens[index] = previous_close * overnight_factors[index]
        closes[index] = opens[index] * intraday_factors[index]
        previous_close = closes[index]
    prices = pd.DataFrame({"open": opens, "close": closes}, index=dates)
    return calculate_returns(prices).daily


def test_all_machine_readable_outputs_are_created(tmp_path: Path) -> None:
    daily = _daily_sample()
    summary = build_summary_statistics(
        daily, annual_risk_free_rate=0.0, trading_days_per_year=252
    )
    comparison = build_component_comparison(summary)
    inferential = build_inferential_tests(daily, bootstrap_samples=500, random_seed=42)
    yearly = build_yearly_statistics(
        daily, annual_risk_free_rate=0.0, trading_days_per_year=252
    )
    robustness = build_robustness_checks(
        daily, trading_days_per_year=252, transaction_cost_bps=1.0
    )
    validation = ValidationReport(
        input_rows=len(daily) + 1,
        input_was_sorted=True,
        timezone_removed=False,
        duplicate_date_rows=0,
        missing_open_rows=0,
        missing_close_rows=0,
        non_numeric_open_rows=0,
        non_numeric_close_rows=0,
        non_positive_open_rows=0,
        non_positive_close_rows=0,
        invalid_rows_removed=0,
        returns_removed_due_to_invalid_previous_row=0,
        final_price_rows=len(daily) + 1,
    )
    metadata = {"project": "test", "maximum_error": 0.0}

    artifacts = write_outputs(
        output_dir=tmp_path,
        daily=daily,
        summary=summary,
        comparison=comparison,
        inferential=inferential,
        yearly=yearly,
        robustness=robustness,
        validation=validation,
        metadata=metadata,
    )

    assert len(artifacts.as_list()) == 8
    assert all(
        path.is_file() and path.stat().st_size > 0 for path in artifacts.as_list()
    )
    loaded_daily = pd.read_csv(artifacts.daily_returns)
    assert len(loaded_daily) == len(daily)
    with artifacts.validation_report.open(encoding="utf-8") as handle:
        validation_json = json.load(handle)
    assert validation_json["first_unaligned_observation_removed"] == 1


def test_all_documented_charts_are_created(tmp_path: Path) -> None:
    daily = _daily_sample()
    yearly = build_yearly_statistics(
        daily, annual_risk_free_rate=0.0, trading_days_per_year=252
    )

    paths = generate_charts(
        daily,
        yearly,
        chart_dir=tmp_path,
        ticker="TEST",
        rolling_window=63,
        trading_days_per_year=252,
    )

    assert len(paths) == 6
    assert all(path.suffix == ".png" for path in paths)
    assert all(path.is_file() and path.stat().st_size > 10_000 for path in paths)
