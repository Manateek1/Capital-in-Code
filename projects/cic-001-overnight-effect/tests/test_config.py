"""Tests for CLI parsing and validation."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from src.config import AnalysisConfig, CacheMode, parse_args


def test_parse_args_accepts_documented_options(tmp_path: Path) -> None:
    config = parse_args(
        [
            "--ticker",
            "qqq",
            "--start-date",
            "2001-01-01",
            "--end-date",
            "2020-12-31",
            "--output-dir",
            str(tmp_path / "output"),
            "--chart-dir",
            str(tmp_path / "charts"),
            "--cache-mode",
            "refresh",
            "--risk-free-rate",
            "0.02",
            "--trading-days-per-year",
            "250",
        ]
    )

    assert config.ticker == "QQQ"
    assert config.start_date == date(2001, 1, 1)
    assert config.end_date == date(2020, 12, 31)
    assert config.cache_mode is CacheMode.REFRESH
    assert config.risk_free_rate == pytest.approx(0.02)
    assert config.trading_days_per_year == 250


@pytest.mark.parametrize(
    "arguments",
    [
        ["--start-date", "2024-01-01", "--end-date", "2024-01-01"],
        ["--ticker", "SPY;DROP"],
        ["--trading-days-per-year", "0"],
        ["--risk-free-rate", "-1"],
        ["--transaction-cost-bps", "-0.1"],
        ["--bootstrap-samples", "99"],
        ["--rolling-window", "1"],
    ],
)
def test_invalid_cli_arguments_exit(arguments: list[str]) -> None:
    with pytest.raises(SystemExit):
        parse_args(arguments)


def test_cache_path_is_stable_and_descriptive(tmp_path: Path) -> None:
    config = AnalysisConfig(
        ticker="BRK-B",
        start_date=date(2010, 1, 1),
        end_date=date(2020, 1, 1),
        cache_dir=tmp_path,
    )

    assert config.cache_path.name == "brk-b_2010-01-01_2020-01-01_adjusted.csv"
