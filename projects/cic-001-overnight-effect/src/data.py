"""Adjusted daily market-data retrieval and local caching."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yfinance as yf

from .config import AnalysisConfig, CacheMode

LOGGER = logging.getLogger(__name__)

Downloader = Callable[..., pd.DataFrame]


class MarketDataError(RuntimeError):
    """Raised when provider or cache data cannot support the analysis."""


@dataclass(frozen=True)
class MarketDataResult:
    """Normalized provider data plus retrieval provenance."""

    prices: pd.DataFrame
    source: str
    cache_path: Path | None
    cache_hit: bool


def normalize_provider_frame(frame: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Extract one ticker's adjusted Open and Close from provider output.

    ``yfinance`` can return ordinary columns or MultiIndex columns whose level
    order varies by version and request shape. This function locates fields by
    name instead of assuming a fixed level order.
    """

    if not isinstance(frame, pd.DataFrame) or frame.empty:
        raise MarketDataError(
            f"market-data provider returned no rows for ticker {ticker!r}"
        )

    columns = list(frame.columns)

    def parts(column: Any) -> tuple[str, ...]:
        if isinstance(column, tuple):
            return tuple(str(item).strip() for item in column)
        return (str(column).strip(),)

    def find_field(field: str) -> Any:
        field_lower = field.lower()
        ticker_lower = ticker.lower()
        matches = [
            column
            for column in columns
            if field_lower in {part.lower() for part in parts(column)}
        ]
        ticker_matches = [
            column
            for column in matches
            if ticker_lower in {part.lower() for part in parts(column)}
        ]
        candidates = ticker_matches or matches
        if len(candidates) != 1:
            rendered = [str(column) for column in candidates]
            raise MarketDataError(
                f"could not uniquely locate {field!r} for {ticker!r}; "
                f"candidates={rendered}"
            )
        return candidates[0]

    open_column = find_field("Open")
    close_column = find_field("Close")
    normalized = pd.DataFrame(
        {
            "Open": frame.loc[:, open_column],
            "Close": frame.loc[:, close_column],
        },
        index=frame.index.copy(),
    )

    parsed_index = pd.DatetimeIndex(pd.to_datetime(normalized.index, errors="coerce"))
    invalid_date_mask = np.asarray(pd.isna(parsed_index), dtype=bool)
    if invalid_date_mask.any():
        invalid_dates = int(invalid_date_mask.sum())
        raise MarketDataError(
            f"provider data contains {invalid_dates} unparseable trading dates"
        )
    normalized.index = pd.DatetimeIndex(parsed_index, name="Date")
    return normalized


def _read_cache(path: Path, ticker: str) -> pd.DataFrame:
    try:
        cached = pd.read_csv(path, index_col="Date", parse_dates=["Date"])
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        raise MarketDataError(
            f"could not read market-data cache {path}: {exc}"
        ) from exc
    return normalize_provider_frame(cached, ticker)


def _write_cache(prices: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    try:
        prices.to_csv(temporary_path, index_label="Date")
        temporary_path.replace(path)
    except OSError as exc:
        temporary_path.unlink(missing_ok=True)
        raise MarketDataError(
            f"could not write market-data cache {path}: {exc}"
        ) from exc


def _validate_requested_coverage(
    prices: pd.DataFrame,
    config: AnalysisConfig,
) -> None:
    dates = pd.DatetimeIndex(prices.index)
    first_date = dates.min().date()
    last_date = dates.max().date()
    expected_last_date = min(config.end_date, date.today())
    oldest_acceptable_last_date = expected_last_date - timedelta(days=10)
    if last_date < oldest_acceptable_last_date:
        raise MarketDataError(
            "market-data response appears partial at the requested end: "
            f"requested_end={config.end_date}, actual_end={last_date}"
        )
    if first_date > config.start_date + timedelta(days=31):
        LOGGER.warning(
            "event=market_data_late_start requested_start=%s actual_start=%s "
            "reason=provider_history_or_ticker_inception",
            config.start_date,
            first_date,
        )


def download_adjusted_prices(
    config: AnalysisConfig,
    downloader: Downloader = yf.download,
) -> pd.DataFrame:
    """Download split- and dividend-adjusted daily Open and Close prices.

    The requested end date is inclusive for this application. ``yfinance``
    treats ``end`` as exclusive, so one calendar day is added to the provider
    request. ``auto_adjust=True`` applies one internally consistent adjustment
    factor to all OHLC fields; raw and adjusted prices are never mixed.
    """

    provider_end = config.end_date + timedelta(days=1)
    try:
        frame = downloader(
            config.ticker,
            start=config.start_date.isoformat(),
            end=provider_end.isoformat(),
            interval="1d",
            auto_adjust=True,
            actions=False,
            progress=False,
            threads=False,
            group_by="column",
        )
    except Exception as exc:  # Provider exceptions are not stable across versions.
        raise MarketDataError(
            f"market-data download failed for {config.ticker!r}: {exc}"
        ) from exc
    return normalize_provider_frame(frame, config.ticker)


def load_market_data(
    config: AnalysisConfig,
    downloader: Downloader = yf.download,
) -> MarketDataResult:
    """Load adjusted prices from cache or the network according to configuration."""

    cache_path = config.cache_path
    if config.cache_mode is CacheMode.USE and cache_path.exists():
        LOGGER.info("event=market_data_cache_hit path=%s", cache_path)
        cached_prices = _read_cache(cache_path, config.ticker)
        _validate_requested_coverage(cached_prices, config)
        return MarketDataResult(
            prices=cached_prices,
            source="local_cache",
            cache_path=cache_path,
            cache_hit=True,
        )

    LOGGER.info(
        "event=market_data_download ticker=%s start=%s end=%s",
        config.ticker,
        config.start_date,
        config.end_date,
    )
    prices = download_adjusted_prices(config, downloader=downloader)
    _validate_requested_coverage(prices, config)
    if config.cache_mode is not CacheMode.OFF:
        _write_cache(prices, cache_path)
        resolved_cache: Path | None = cache_path
    else:
        resolved_cache = None

    return MarketDataResult(
        prices=prices,
        source="yfinance",
        cache_path=resolved_cache,
        cache_hit=False,
    )
