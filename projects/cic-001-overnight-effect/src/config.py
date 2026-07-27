"""Configuration and command-line parsing for the CIC-001 analysis."""

from __future__ import annotations

import argparse
import re
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path

DEFAULT_TICKER = "SPY"
DEFAULT_START_DATE = date(1994, 1, 1)
DEFAULT_END_DATE = date(2025, 12, 31)
DEFAULT_TRADING_DAYS = 252
DEFAULT_RISK_FREE_RATE = 0.0
DEFAULT_ROLLING_WINDOW = 63
DEFAULT_BOOTSTRAP_SAMPLES = 10_000
DEFAULT_RANDOM_SEED = 42
DEFAULT_TRANSACTION_COST_BPS = 1.0

_TICKER_PATTERN = re.compile(r"^[A-Z0-9.^=-]{1,20}$")


class CacheMode(StrEnum):
    """Supported behaviors for the local market-data cache."""

    USE = "use"
    REFRESH = "refresh"
    OFF = "off"


@dataclass(frozen=True)
class AnalysisConfig:
    """Validated settings for one reproducible analysis run."""

    ticker: str = DEFAULT_TICKER
    start_date: date = DEFAULT_START_DATE
    end_date: date = DEFAULT_END_DATE
    output_dir: Path = Path("results")
    chart_dir: Path = Path("charts")
    cache_dir: Path = Path("data/raw")
    cache_mode: CacheMode = CacheMode.USE
    risk_free_rate: float = DEFAULT_RISK_FREE_RATE
    trading_days_per_year: int = DEFAULT_TRADING_DAYS
    rolling_window: int = DEFAULT_ROLLING_WINDOW
    bootstrap_samples: int = DEFAULT_BOOTSTRAP_SAMPLES
    random_seed: int = DEFAULT_RANDOM_SEED
    transaction_cost_bps: float = DEFAULT_TRANSACTION_COST_BPS

    def __post_init__(self) -> None:
        normalized_ticker = self.ticker.strip().upper()
        object.__setattr__(self, "ticker", normalized_ticker)

        if not _TICKER_PATTERN.fullmatch(normalized_ticker):
            raise ValueError(
                "ticker must contain 1-20 letters, numbers, or the symbols . ^ = -"
            )
        if self.start_date >= self.end_date:
            raise ValueError("start date must be earlier than end date")
        if self.risk_free_rate <= -1.0:
            raise ValueError("risk-free rate must be greater than -1.0")
        if self.trading_days_per_year <= 0:
            raise ValueError("trading days per year must be positive")
        if self.rolling_window <= 1:
            raise ValueError("rolling window must be greater than 1")
        if self.bootstrap_samples < 100:
            raise ValueError("bootstrap samples must be at least 100")
        if self.transaction_cost_bps < 0.0:
            raise ValueError("transaction cost must be non-negative")
        if self.transaction_cost_bps >= 10_000.0:
            raise ValueError("transaction cost must be less than 10,000 basis points")

    @property
    def cache_path(self) -> Path:
        """Return the deterministic cache file for this request."""

        safe_ticker = re.sub(r"[^A-Z0-9]+", "-", self.ticker).strip("-").lower()
        filename = (
            f"{safe_ticker}_{self.start_date.isoformat()}_"
            f"{self.end_date.isoformat()}_adjusted.csv"
        )
        return self.cache_dir / filename

    def as_metadata(self) -> dict[str, object]:
        """Return settings in a JSON-serializable form."""

        values = asdict(self)
        values["start_date"] = self.start_date.isoformat()
        values["end_date"] = self.end_date.isoformat()
        values["output_dir"] = str(self.output_dir.resolve())
        values["chart_dir"] = str(self.chart_dir.resolve())
        values["cache_dir"] = str(self.cache_dir.resolve())
        values["cache_mode"] = self.cache_mode.value
        return values


def _iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"{value!r} is not a valid ISO date (YYYY-MM-DD)"
        ) from exc


def build_parser() -> argparse.ArgumentParser:
    """Build the CIC-001 command-line parser."""

    parser = argparse.ArgumentParser(
        prog="python -m src.main",
        description=(
            "Compare adjusted overnight and regular-hours returns using daily "
            "market data."
        ),
    )
    parser.add_argument("--ticker", default=DEFAULT_TICKER)
    parser.add_argument(
        "--start-date",
        type=_iso_date,
        default=DEFAULT_START_DATE,
        help="inclusive requested start date (default: %(default)s)",
    )
    parser.add_argument(
        "--end-date",
        type=_iso_date,
        default=DEFAULT_END_DATE,
        help="inclusive requested end date (default: %(default)s)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results"),
        help="directory for generated CSV and JSON files",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("data/raw"),
        help="directory for ignored downloaded market-data cache files",
    )
    parser.add_argument(
        "--chart-dir",
        type=Path,
        default=Path("charts"),
        help="directory for generated publication-quality chart files",
    )
    parser.add_argument(
        "--cache-mode",
        choices=[mode.value for mode in CacheMode],
        default=CacheMode.USE.value,
        help="use an existing cache, refresh it, or disable caching",
    )
    parser.add_argument(
        "--risk-free-rate",
        type=float,
        default=DEFAULT_RISK_FREE_RATE,
        help="annual decimal risk-free rate used for Sharpe ratios",
    )
    parser.add_argument(
        "--trading-days-per-year",
        type=int,
        default=DEFAULT_TRADING_DAYS,
        help="annualization convention (default: %(default)s)",
    )
    parser.add_argument(
        "--rolling-window",
        type=int,
        default=DEFAULT_ROLLING_WINDOW,
        help="trading-day window for rolling-average charts",
    )
    parser.add_argument(
        "--bootstrap-samples",
        type=int,
        default=DEFAULT_BOOTSTRAP_SAMPLES,
        help="paired resamples for the mean-difference confidence interval",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=DEFAULT_RANDOM_SEED,
        help="random seed for reproducible bootstrap results",
    )
    parser.add_argument(
        "--transaction-cost-bps",
        type=float,
        default=DEFAULT_TRANSACTION_COST_BPS,
        help="hypothetical one-way cost per trade leg, in basis points",
    )
    return parser


def parse_args(argv: Sequence[str] | None = None) -> AnalysisConfig:
    """Parse and validate command-line arguments."""

    parser = build_parser()
    namespace = parser.parse_args(argv)
    try:
        return AnalysisConfig(
            ticker=namespace.ticker,
            start_date=namespace.start_date,
            end_date=namespace.end_date,
            output_dir=namespace.output_dir,
            chart_dir=namespace.chart_dir,
            cache_dir=namespace.cache_dir,
            cache_mode=CacheMode(namespace.cache_mode),
            risk_free_rate=namespace.risk_free_rate,
            trading_days_per_year=namespace.trading_days_per_year,
            rolling_window=namespace.rolling_window,
            bootstrap_samples=namespace.bootstrap_samples,
            random_seed=namespace.random_seed,
            transaction_cost_bps=namespace.transaction_cost_bps,
        )
    except ValueError as exc:
        parser.error(str(exc))
        raise AssertionError("argparse.error must terminate") from exc
