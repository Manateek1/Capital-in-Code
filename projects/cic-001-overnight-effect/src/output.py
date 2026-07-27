"""Stable CSV and JSON output for the CIC-001 research run."""

from __future__ import annotations

import json
import os
import platform
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import __version__
from .config import AnalysisConfig
from .data import MarketDataResult
from .validation import ValidationReport

PACKAGE_NAMES = ("numpy", "pandas", "scipy", "matplotlib", "yfinance")


@dataclass(frozen=True)
class OutputArtifacts:
    """Paths of all generated machine-readable result files."""

    daily_returns: Path
    summary_statistics: Path
    component_comparison: Path
    inferential_tests: Path
    yearly_statistics: Path
    robustness_checks: Path
    validation_report: Path
    run_metadata: Path

    def as_list(self) -> list[Path]:
        """Return artifacts in stable presentation order."""

        return [
            self.daily_returns,
            self.summary_statistics,
            self.component_comparison,
            self.inferential_tests,
            self.yearly_statistics,
            self.robustness_checks,
            self.validation_report,
            self.run_metadata,
        ]


def _json_default(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        if np.isnan(value):
            return None
        return float(value)
    if isinstance(value, (Path,)):
        return str(value)
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    raise TypeError(f"object of type {type(value).__name__} is not JSON serializable")


def _atomic_csv(frame: pd.DataFrame, path: Path, *, index: bool) -> None:
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    frame.to_csv(temporary, index=index, float_format="%.12g")
    os.replace(temporary, path)


def _atomic_json(payload: dict[str, Any], path: Path) -> None:
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(
            payload,
            handle,
            indent=2,
            sort_keys=True,
            allow_nan=False,
            default=_json_default,
        )
        handle.write("\n")
    os.replace(temporary, path)


def package_versions() -> dict[str, str]:
    """Return installed versions for the reproducibility record."""

    versions: dict[str, str] = {}
    for package in PACKAGE_NAMES:
        try:
            versions[package] = version(package)
        except PackageNotFoundError:
            versions[package] = "not-installed"
    return versions


def build_run_metadata(
    config: AnalysisConfig,
    market_data: MarketDataResult,
    clean_prices: pd.DataFrame,
    daily: pd.DataFrame,
    *,
    maximum_reconstruction_error: float,
) -> dict[str, Any]:
    """Build a complete provenance and methodology record."""

    return {
        "project": "CIC-001 - The Overnight Effect",
        "pipeline_version": __version__,
        "run_timestamp_utc": datetime.now(UTC).isoformat(),
        "configuration": config.as_metadata(),
        "data": {
            "provider": "Yahoo Finance via yfinance",
            "retrieval_source": market_data.source,
            "cache_hit": market_data.cache_hit,
            "cache_path": (
                str(market_data.cache_path.resolve())
                if market_data.cache_path is not None
                else None
            ),
            "adjustment_method": (
                "yfinance auto_adjust=True; the provider's split- and "
                "dividend-adjustment factor is applied consistently to Open and Close"
            ),
            "actual_first_price_date": clean_prices.index.min().date().isoformat(),
            "actual_last_price_date": clean_prices.index.max().date().isoformat(),
            "actual_first_return_date": daily.index.min().date().isoformat(),
            "actual_last_return_date": daily.index.max().date().isoformat(),
            "clean_price_observations": len(clean_prices),
            "aligned_return_observations": len(daily),
        },
        "methodology": {
            "overnight_simple_return": "current_open / previous_close - 1",
            "intraday_simple_return": "current_close / current_open - 1",
            "close_to_close_simple_return": "current_close / previous_close - 1",
            "first_observation_removed": True,
            "annualization": (f"{config.trading_days_per_year} trading days per year"),
            "annual_risk_free_rate_decimal": config.risk_free_rate,
            "maximum_return_reconstruction_error": maximum_reconstruction_error,
            "reconstruction_tolerance": 1e-12,
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "package_versions": package_versions(),
        },
    }


def write_outputs(
    *,
    output_dir: Path,
    daily: pd.DataFrame,
    summary: pd.DataFrame,
    comparison: pd.DataFrame,
    inferential: pd.DataFrame,
    yearly: pd.DataFrame,
    robustness: dict[str, Any],
    validation: ValidationReport,
    metadata: dict[str, Any],
) -> OutputArtifacts:
    """Write all required machine-readable outputs atomically."""

    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts = OutputArtifacts(
        daily_returns=output_dir / "daily_returns.csv",
        summary_statistics=output_dir / "summary_statistics.csv",
        component_comparison=output_dir / "component_comparison.csv",
        inferential_tests=output_dir / "inferential_tests.csv",
        yearly_statistics=output_dir / "yearly_statistics.csv",
        robustness_checks=output_dir / "robustness_checks.json",
        validation_report=output_dir / "data_validation_report.json",
        run_metadata=output_dir / "run_metadata.json",
    )

    daily_for_output = daily.copy()
    daily_for_output.index.name = "date"
    _atomic_csv(daily_for_output, artifacts.daily_returns, index=True)
    _atomic_csv(summary, artifacts.summary_statistics, index=False)
    _atomic_csv(comparison, artifacts.component_comparison, index=False)
    _atomic_csv(inferential, artifacts.inferential_tests, index=False)
    _atomic_csv(yearly, artifacts.yearly_statistics, index=False)
    _atomic_json(robustness, artifacts.robustness_checks)
    _atomic_json(
        validation.as_dict(final_return_rows=len(daily)),
        artifacts.validation_report,
    )
    _atomic_json(metadata, artifacts.run_metadata)
    return artifacts
