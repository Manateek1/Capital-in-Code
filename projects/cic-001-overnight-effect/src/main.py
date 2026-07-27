"""Command-line entrypoint for the complete CIC-001 research pipeline."""

from __future__ import annotations

import logging
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from .charts import generate_charts
from .config import AnalysisConfig, parse_args
from .data import MarketDataError, load_market_data
from .output import OutputArtifacts, build_run_metadata, write_outputs
from .returns import ReturnCalculationError, calculate_returns
from .robustness import build_robustness_checks
from .stats import (
    build_component_comparison,
    build_inferential_tests,
    build_summary_statistics,
    build_yearly_statistics,
)
from .validation import DataValidationError, validate_and_clean_prices

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class RunResult:
    """Artifacts and key facts returned by a successful pipeline run."""

    result_files: OutputArtifacts
    chart_files: list[Path]
    actual_start_date: str
    actual_end_date: str
    observations: int
    maximum_reconstruction_error: float
    cache_hit: bool


def configure_logging() -> None:
    """Configure concise key-value-friendly logs for command-line runs."""

    logging.basicConfig(
        level=logging.INFO,
        format=("%(asctime)s level=%(levelname)s logger=%(name)s message=%(message)s"),
    )


def run_analysis(config: AnalysisConfig) -> RunResult:
    """Execute download, validation, analysis, charts, and file output."""

    LOGGER.info(
        "event=analysis_started ticker=%s requested_start=%s requested_end=%s",
        config.ticker,
        config.start_date,
        config.end_date,
    )
    market_data = load_market_data(config)
    clean_prices, validation = validate_and_clean_prices(market_data.prices)
    calculations = calculate_returns(clean_prices)
    daily = calculations.daily
    if len(daily) < config.rolling_window:
        raise DataValidationError(
            "not enough aligned returns for the configured rolling window: "
            f"required={config.rolling_window}, available={len(daily)}"
        )

    LOGGER.info(
        "event=data_validated input_rows=%d clean_rows=%d return_rows=%d "
        "invalid_rows_removed=%d",
        validation.input_rows,
        validation.final_price_rows,
        len(daily),
        validation.invalid_rows_removed,
    )
    LOGGER.info(
        "event=alignment_verified maximum_reconstruction_error=%.3e",
        calculations.maximum_reconstruction_error,
    )

    summary = build_summary_statistics(
        daily,
        annual_risk_free_rate=config.risk_free_rate,
        trading_days_per_year=config.trading_days_per_year,
    )
    comparison = build_component_comparison(summary)
    inferential = build_inferential_tests(
        daily,
        bootstrap_samples=config.bootstrap_samples,
        random_seed=config.random_seed,
    )
    yearly = build_yearly_statistics(
        daily,
        annual_risk_free_rate=config.risk_free_rate,
        trading_days_per_year=config.trading_days_per_year,
    )
    robustness = build_robustness_checks(
        daily,
        trading_days_per_year=config.trading_days_per_year,
        transaction_cost_bps=config.transaction_cost_bps,
    )
    metadata = build_run_metadata(
        config,
        market_data,
        clean_prices,
        daily,
        maximum_reconstruction_error=calculations.maximum_reconstruction_error,
    )
    result_files = write_outputs(
        output_dir=config.output_dir,
        daily=daily,
        summary=summary,
        comparison=comparison,
        inferential=inferential,
        yearly=yearly,
        robustness=robustness,
        validation=validation,
        metadata=metadata,
    )
    chart_files = generate_charts(
        daily,
        yearly,
        chart_dir=config.chart_dir,
        ticker=config.ticker,
        rolling_window=config.rolling_window,
        trading_days_per_year=config.trading_days_per_year,
    )

    actual_start = daily.index.min().date().isoformat()
    actual_end = daily.index.max().date().isoformat()
    LOGGER.info(
        "event=analysis_completed actual_start=%s actual_end=%s observations=%d "
        "result_files=%d chart_files=%d",
        actual_start,
        actual_end,
        len(daily),
        len(result_files.as_list()),
        len(chart_files),
    )
    return RunResult(
        result_files=result_files,
        chart_files=chart_files,
        actual_start_date=actual_start,
        actual_end_date=actual_end,
        observations=len(daily),
        maximum_reconstruction_error=calculations.maximum_reconstruction_error,
        cache_hit=market_data.cache_hit,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Parse arguments and return a process exit code."""

    configure_logging()
    config = parse_args(argv)
    try:
        run_analysis(config)
    except (
        MarketDataError,
        DataValidationError,
        ReturnCalculationError,
        OSError,
        ValueError,
    ) as exc:
        LOGGER.error(
            "event=analysis_failed error_type=%s error=%s",
            type(exc).__name__,
            exc,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
