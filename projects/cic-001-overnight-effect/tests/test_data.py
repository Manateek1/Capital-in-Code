"""Offline tests for provider-shape normalization and caching."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from src.config import AnalysisConfig, CacheMode
from src.data import MarketDataError, load_market_data, normalize_provider_frame


def test_normalize_yfinance_field_first_multiindex() -> None:
    index = pd.to_datetime(["2024-01-02", "2024-01-03"])
    columns = pd.MultiIndex.from_tuples(
        [("Open", "SPY"), ("Close", "SPY"), ("Volume", "SPY")]
    )
    frame = pd.DataFrame(
        [[100.0, 101.0, 10], [102.0, 103.0, 20]],
        index=index,
        columns=columns,
    )

    result = normalize_provider_frame(frame, "SPY")

    assert list(result.columns) == ["Open", "Close"]
    assert result.iloc[1].to_dict() == {"Open": 102.0, "Close": 103.0}


def test_normalize_yfinance_ticker_first_multiindex() -> None:
    index = pd.to_datetime(["2024-01-02", "2024-01-03"])
    columns = pd.MultiIndex.from_tuples(
        [("SPY", "Open"), ("SPY", "Close"), ("SPY", "High")]
    )
    frame = pd.DataFrame(
        [[100.0, 101.0, 102.0], [103.0, 104.0, 105.0]],
        index=index,
        columns=columns,
    )

    result = normalize_provider_frame(frame, "SPY")

    assert result["Open"].tolist() == [100.0, 103.0]
    assert result["Close"].tolist() == [101.0, 104.0]


@pytest.mark.parametrize(
    "frame",
    [
        pd.DataFrame(),
        pd.DataFrame(
            {"Open": [100.0]},
            index=pd.to_datetime(["2024-01-02"]),
        ),
        pd.DataFrame(
            {"Open": [100.0], "Close": [101.0]},
            index=["not-a-date"],
        ),
    ],
)
def test_malformed_provider_output_raises(frame: pd.DataFrame) -> None:
    with pytest.raises(MarketDataError):
        normalize_provider_frame(frame, "SPY")


def test_download_uses_inclusive_application_end_date(tmp_path: Path) -> None:
    calls: dict[str, Any] = {}

    def fake_downloader(*args: Any, **kwargs: Any) -> pd.DataFrame:
        calls["args"] = args
        calls["kwargs"] = kwargs
        return pd.DataFrame(
            {"Open": [100.0, 101.0], "Close": [101.0, 102.0]},
            index=pd.to_datetime(["2024-01-02", "2024-01-03"]),
        )

    config = AnalysisConfig(
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 3),
        cache_dir=tmp_path,
        cache_mode=CacheMode.OFF,
    )
    result = load_market_data(config, downloader=fake_downloader)

    assert calls["kwargs"]["end"] == "2024-01-04"
    assert calls["kwargs"]["auto_adjust"] is True
    assert result.cache_path is None
    assert not result.cache_hit


def test_cache_is_reused_without_network(tmp_path: Path) -> None:
    config = AnalysisConfig(
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 3),
        cache_dir=tmp_path,
        cache_mode=CacheMode.USE,
    )
    cached = pd.DataFrame(
        {"Open": [100.0, 101.0], "Close": [101.0, 102.0]},
        index=pd.to_datetime(["2024-01-02", "2024-01-03"]),
    )
    cached.to_csv(config.cache_path, index_label="Date")

    def failing_downloader(*args: Any, **kwargs: Any) -> pd.DataFrame:
        raise AssertionError("network should not be used on a cache hit")

    result = load_market_data(config, downloader=failing_downloader)

    assert result.cache_hit
    assert result.source == "local_cache"
    assert len(result.prices) == 2


def test_provider_exception_is_wrapped_with_context(tmp_path: Path) -> None:
    config = AnalysisConfig(
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 3),
        cache_dir=tmp_path,
        cache_mode=CacheMode.OFF,
    )

    def failing_downloader(*args: Any, **kwargs: Any) -> pd.DataFrame:
        raise ConnectionError("synthetic network failure")

    with pytest.raises(
        MarketDataError,
        match=r"market-data download failed.*synthetic network failure",
    ):
        load_market_data(config, downloader=failing_downloader)


def test_partial_provider_response_at_requested_end_raises(tmp_path: Path) -> None:
    config = AnalysisConfig(
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        cache_dir=tmp_path,
        cache_mode=CacheMode.OFF,
    )

    def partial_downloader(*args: Any, **kwargs: Any) -> pd.DataFrame:
        return pd.DataFrame(
            {"Open": [100.0, 101.0], "Close": [101.0, 102.0]},
            index=pd.to_datetime(["2024-01-02", "2024-01-03"]),
        )

    with pytest.raises(MarketDataError, match="appears partial"):
        load_market_data(config, downloader=partial_downloader)
